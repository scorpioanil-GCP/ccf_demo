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
**Amended by ``C-08`` (Phase 19): what it hands back is the producer half's
canonical** ``bytes``\\ **, which the codec parses into that same shape.** The
invisibility claim is unchanged and is the reason the retype cost nothing here.

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

**And since ``C-07`` (Phase 19) it serializes the** *question* **too, which is
what makes the argument above cover both halves.** :meth:`InProcessAdapter.ask`
encodes the caller's :class:`~ccf.client.wire.WireRequest` and hands
:meth:`InProcessAdapter._door` **text**; the door half parses it with
:func:`~ccf.products.door.door_question` and echoes what **it** parsed. Until
then in-process was a degenerate wire in one direction only: the answer
crossed a real serialization while the question was passed as the very object
the client held, so the client's echo cross-check compared an object with
itself on the transport every quickstart, fixture and dev path uses — which is
``D-IMPL-151`` finding ``B0`` surviving here while being closed over the wire.

The extra cost is **two more serializations per ask** — the question out and
the question back in — and ``C-14`` accepts it with **no benchmark owed**:
``D-13`` already accepted *"a microsecond of serialization"* on the answer
half, and a question is far smaller than an answer. No performance claim is
made here in either direction, because none was measured.

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
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    BindingDocument,
    conforming_plan_factory,
    load_binding_document,
    load_reference,
)
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.errors import BindingError
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneProtocol, ControlPlaneRegistry
from ccf.deployment import BootedFabric
from ccf.deployment.config import load_config_and_boot
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.door import door_answer, door_question
from ccf.products.request import ProductRequest
from ccf.products.resolver import (
    ProductNotResolvable,
    ServedProductResolverProtocol,
    build_governed_resolver,
)

__ccf_mode__ = "algorithmic"

__all__ = ["SCHEME", "InProcessAdapter", "reset_boot_cache"]


#: The scheme this adapter answers to. Written once, so the registry entry, the
#: refusal messages and the tests all say the same string.
SCHEME = "inprocess"

#: One Control Plane artifact class, for :func:`_artifact`'s narrowing refusal.
_A = TypeVar("_A")


@dataclass(frozen=True)
class _BootedDeployment:
    """One deployment, booted once, with everything a question needs.

    Frozen and handle-carrying for the reason
    :class:`~ccf.deployment.BootedFabric` gives for its own shape: a live
    handle has no canonical serialization and never belongs in a content hash.

    ``document`` rides along because the question vocabulary is now **data**
    (``D-IMPL-141``): the request this adapter builds is assembled from the
    binding document rather than produced by a deployment factory, so the
    document has to outlive the boot.
    """

    fabric: BootedFabric
    control_plane: ControlPlaneProtocol
    resolver: ServedProductResolverProtocol
    document: BindingDocument
    schema_version: str


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


def _artifact(fabric: BootedFabric, *, key: str, expected: type[_A]) -> _A:
    """One parsed artifact off the booted fabric, narrowed by name.

    A refusal rather than a ``cast``: ``binding.yaml`` is hand-authored, so a
    key naming the *wrong section* of ``ccf_config.yaml`` is an ordinary
    authoring mistake. Told here it names the key and the class; discovered
    later it is an ``AttributeError`` inside a scorer.
    """
    try:
        artifact = fabric.artifacts[key]
    except KeyError as absent:
        raise BindingError(
            f"`{key}` in {BINDING_DOCUMENT_NAME} names a Control Plane key this"
            " deployment does not have — it holds"
            f" {', '.join(f'`{name}`' for name in sorted(fabric.artifacts))}"
        ) from absent
    if not isinstance(artifact, expected):
        raise BindingError(
            f"`{key}` in {BINDING_DOCUMENT_NAME} names a"
            f" `{type(artifact).__name__}`, not a `{expected.__name__}`"
        )
    return artifact


def _boot(document: BindingDocument) -> _BootedDeployment:
    """Boot one deployment and build its resolver. Called at most once per root.

    **The SDK builds the resolver here** — that is what ``D-IMPL-141``'s ruling
    changed. Every value the composition needs is data the deployment declared,
    except the one thing measurement said cannot be data: the projection, which
    arrives through the single permitted ``plan:`` reference (Amendment A.3).

    **The composition itself is not written here.** It lives in
    :func:`~ccf.products.resolver.build_governed_resolver`, which is where the
    SDK selects its own reference debt scorer when a caller passes none — so a
    second transport joins by calling one function rather than by growing a
    second copy of a thirteen-argument construction, and the *"a deployment
    that provides only data never has to know the Protocol exists"* property
    (2026-08-16 spec §6) belongs to the seam rather than to this adapter.

    One reference implementation is still selected *here*, and deliberately:
    :class:`~ccf.artifacts.file_store.FileArtifactStore`, the shipped
    file-backed store (CLAUDE.md §7.4), because ``artifact_store:`` declares a
    **path** and a path is what a file-backed store takes. The helper is typed
    to an :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` so it stays
    substrate-agnostic; turning *this deployment's declared path* into *a
    store* is the transport's act, and a deployment on another substrate
    changes this line and nothing in ``ccf.products``.
    """
    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        document.config, registry=control_plane, connection=document.connection
    )
    plan_factory = conforming_plan_factory(
        load_reference(document.plan, root=document.root, key="plan"),
        reference=document.plan,
        root=document.root,
    )
    declaration = _artifact(
        fabric, key=document.product_class_key, expected=ProductClassDeclaration
    )
    try:
        resolver = build_governed_resolver(
            fabric=fabric,
            control_plane=control_plane,
            product_class_key=document.product_class_key,
            request_contract_key=document.request_contract_key,
            operator_parameter_keys=document.operator_parameter_keys,
            policy_bundle_key=document.policy_bundle_key,
            plan_factory=plan_factory,
            # The deployment's declaration of what its own mechanism writes and
            # under which kind (D-IMPL-353 §1.2): the two classes the binding
            # document names and the SDK's admitted-child class, all
            # `ReplayMint`. This adapter is a composition site; the resolver it
            # builds mints its own capabilities against this declaration and
            # refuses at construction if a class it files is missing.
            artifact_store=FileArtifactStore(
                root=document.artifact_store,
                write_kinds=WriteKinds.declare(
                    {
                        document.replay_record_class: (ReplayMint,),
                        document.query_pin_class: (ReplayMint,),
                        ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
                    }
                ),
            ),
            replay_record_class=document.replay_record_class,
            query_pin_class=document.query_pin_class,
            max_ttl_seconds=document.max_ttl_seconds,
            product_ttl_seconds=document.product_ttl_seconds,
            half_life_key=document.debt.half_life_key,
            debt_profile_key=document.debt.debt_profile_key,
            declared_completeness=document.debt.completeness,
            declared_semantic_consistency=document.debt.semantic_consistency,
        )
    except ProductNotResolvable as unwired:
        # Translated, not swallowed. The helper's refusal names a *manifest*
        # key, which is correct where it is raised and incomplete here: at boot
        # every key it could miss was written in `binding.yaml`, so the adopter
        # is told which document to edit rather than being left to infer it.
        # The original is chained, so nothing about the manifest is lost.
        raise BindingError(
            f"`debt:` in {BINDING_DOCUMENT_NAME} names a Control Plane key this"
            f" deployment does not have — {unwired}"
        ) from unwired
    return _BootedDeployment(
        fabric=fabric,
        control_plane=control_plane,
        resolver=resolver,
        document=document,
        schema_version=declaration.schema_version,
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

    __slots__ = ("_address", "_resolver")

    def __init__(self, address: str) -> None:
        self._address = address

    def ask(self, request: WireRequest) -> bytes:
        """Boot if needed, encode the question, and hand it to the door half.

        This is the **client** half of a degenerate wire that is now degenerate
        in both directions (``C-07``, Phase 19). It encodes the question and
        passes *text* to :meth:`_door`; it never passes the
        :class:`~ccf.client.wire.WireRequest` object, because two halves sharing
        one object would make the echo cross-check cosmetic on the transport
        every quickstart, fixture and dev path uses.

        Raises:
            ccf.client.errors.BindingError: the address names no deployment, or
                its binding document is unusable. A
                :class:`~ccf.client.errors.TransportError` by inheritance, so
                one ``except`` clause still covers every way the wire never
                spoke.
            ccf.products.request.ProductRequestViolation: the question the
                binding document declared is not a well-formed request. Raised
                at :class:`~ccf.products.request.ProductRequest` construction
                rather than caught and re-wrapped, because a malformed declared
                question is deployment wiring being wrong and not the wire
                failing to speak.
            ccf.products.resolver.ProductNotResolvable: the deployment is
                wired to serve a different class than the one asked for.
                Deliberately **not** converted into a refusal: a mis-wiring
                reported as a governed "no" would have a caller record an
                audited refusal the fabric never made.
        """
        booted = self._ensure_booted()
        # `D-04` says `as_of=None` means *the server's decision instant*,
        # and `~ccf.client.client.ProductClient.ask` spells that out as the
        # producing deployment answering "against its own clock". This read
        # the DECLARED `question.asked_at` instead, so the default path
        # answered as of a literal in `binding.yaml` — and a deployment
        # whose declared instant had passed printed an answer that had
        # already expired. Measured at the Phase 17 close review: with no
        # `--as-of`, the shipped example reported `answer expires
        # 2026-03-02 12:10:00+00:00` on 2026-08-16, five and a half months
        # stale, while its README promised "today's answer".
        #
        # Ruled by Dave 2026-08-16: `None` means NOW. A caller who needs a
        # reproducible address passes an explicit boundary, which is what
        # the documented command does and why its content address is stable.
        #
        # `C-15` (Phase 19) kept this read exactly where it is and moved
        # nothing to the door: the ENCODED question below carries
        # `temporal_boundary=None` unchanged, so the echo comes back `None`
        # as `C-02` requires, and the resolved instant travels to the door
        # half as a separate argument — mirroring `mcp+stdio`, where
        # `asked_at` is a separate tool argument.
        asked_at = request.temporal_boundary or datetime.now(UTC)
        return self._door(
            canonical_bytes(request).decode("utf-8"),
            asked_at=asked_at,
            booted=booted,
        )

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
        return booted

    def _door(
        self,
        asked_json: str,
        *,
        asked_at: datetime,
        booted: _BootedDeployment,
    ) -> bytes:
        """The producer half — parse the encoded question, answer it, emit bytes.

        **It takes text and never a** :class:`~ccf.client.wire.WireRequest`
        **object**, and that is the whole of ``C-07``: a door handed the very
        object the client half constructed would echo the caller's own copy
        back to the caller, and the client's echo cross-check would be an
        object compared with itself on the transport every quickstart, fixture
        and dev path uses — which is ``D-IMPL-151`` finding ``B0`` surviving
        in-process while being closed over the wire. The two extra
        serializations this costs per ``ask`` are the accepted price ``C-14``
        ruled on, with no benchmark owed: ``D-13`` already accepted *"a
        microsecond of serialization"* on the answer half, and the question is
        far smaller than the answer.

        The emission itself is :func:`~ccf.products.door.door_answer`, the one
        site where the shape is built: the vessel is serialized exactly once
        and the content address is ``sha256`` of those same bytes, so the
        client's recomputation is exact by construction rather than by two
        implementations agreeing. ``asked_at`` arrives as a separate argument
        rather than off the echo because the two are different facts — the
        instant the door answers at, and the boundary the caller asked for,
        which may be ``None`` (``C-02``, ``C-15``).
        """
        asked_wire = door_question(asked_json)
        document = booted.document
        typed = ProductRequest(
            schema_name=asked_wire.product_id,
            schema_version=booted.schema_version,
            subject=document.question.subject,
            intent=document.question.intent,
            freshness=document.question.freshness,
            asked_at=asked_at,
            # Resolved from the DECODED question rather than from the object
            # the client half held (`C-01`): one source for what is answered,
            # and the echo `door_answer` puts on the wire is that same source.
            parameters=dict(asked_wire.parameters),
        )
        resolved = self._resolver(
            tenant=booted.fabric.tenant_id,
            product_class=typed.schema_name,
            version=typed.schema_version,
            perspective=document.perspective,
            request=typed,
        )
        return door_answer(resolved, echo=asked_wire, resolved_request=typed)


SCHEME_REGISTRY[SCHEME] = InProcessAdapter
