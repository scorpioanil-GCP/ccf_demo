"""The composition root — the one place a ``GraphWriter`` is constructed.

SDK-defined mechanism (CLAUDE.md §10; the whitepaper specifies the
single-writer *invariant*, not the wiring that realizes it). DESIGN.md §2A.5.3
names this module as layer 2 of the D-IMPL-41 stack: the composition root
constructs exactly one ``GraphWriter`` and injects it into L2 and nowhere else.

Everything the single-writer invariant rests on converges here, so it is worth
stating what each part is doing:

* The write surface is import-restricted by the CINV-02 lint, and since D-01
  that surface is a *class* of modules rather than one file: the neutral base
  :mod:`ccf.graph._writer` plus every ``ccf.graph.backends.<name>_write``.
  This module and ``ccf.assembly`` are the permitted importers of a
  per-adapter write module; the neutral base additionally permits the backend
  registry, which types the seam without exercising it. A module that wanted a
  write handle would have to name one of those imports, and naming it fails
  CI. **This module now names none of them.** It asks
  :func:`ccf.graph.registry.resolve` for the adapter a deployment selected and
  calls the two factories that adapter registered, so the write module is
  reached through the record rather than through an import here.
* The token is minted once per graph and consumed by the one writer. A second
  boot against the same graph raises before any write can occur, rather than
  producing a second writer that quietly interleaves state the replay engine
  could never reconstruct.
* :class:`FabricHandle` exposes a reader, the worker, the Control Plane, and
  the adapter pin. It has no writer attribute — not a private one either.
  Shutdown runs through a closure, so there is nothing on the handle to reach
  for.
* **A read-only boot mints no writer at all** (FW-2, whole-branch review I-1;
  ``D-IMPL-374``). ``boot(..., read_only=True)`` opens the reader and mints the
  classification authority from the pinned resolution spec through the same
  private mint path as the writer boot, but never mints a boot token, so it
  takes no writer lease and marks no graph live. It neither validates nor
  uses the connection's writer-lease setting (N-2). It writes no graph
  content, but it is not write-free at the substrate (N-6): opening the store
  still runs the store's own open-time setup, as a writer boot's open does
  (schema creation; a Fluree ledger's creation). Its worker's writer refuses
  every write by name (:class:`ReadOnlyFabricRefused`). It exists so replay —
  whitepaper §7.10 — can read a classification decision beside the live
  writer of a persistent store, in another process.

**Honest residual claim, verbatim from DESIGN.md §9 (per the D-IMPL-41
ruling):** Python cannot make determined-insider evasion impossible. The claim
strength is *no unforced path exists, and every forced path fails CI or fails
at boot* — never a claim of absolute prevention. Every statement in this module
about single-writer enforcement carries exactly that strength and no more.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Final, Literal, NoReturn

from ccf.assembly.worker import (
    AssemblyWorker,
    EntityResolutionSpec,
    SpecDrivenEntityResolution,
)
from ccf.authz.capability import (
    CompositionRegister,
    COMPOSITION_PRINCIPAL,
    Authorized,
    Register,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph._writer import adopt_writer, mint_boot_token, release_boot_token
from ccf.contracts.claims import EntityClaim, RelationshipClaim
from ccf.graph.protocols import (
    ClassificationAuthority,
    GraphReader,
    UpsertResult,
    WriterLeaseScope,
)
from ccf.controlplane.invalidation import ControlPlaneInvalidationSink, register_key
from ccf.graph.leases import _without_lock_directory_setting
from ccf.graph.registry import (
    AdapterPin,
    BackendStore,
    ResolvedSecret,
    resolve,
    validate_connection,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "READ_ONLY_LEASE_MECHANISM",
    "READ_ONLY_LEASE_SCOPE",
    "FabricHandle",
    "ReadOnlyFabricRefused",
    "boot",
]

#: What :attr:`FabricHandle.lease_scope` reports for a read-only boot (FW-2;
#: ``D-IMPL-374``): no writer was minted, so no writer lease was taken and no
#: exclusion of any scope is held. Mechanism vocabulary, beside the two
#: :data:`~ccf.graph.protocols.WriterLeaseScope` values a writer boot reports.
READ_ONLY_LEASE_SCOPE: Final[Literal["read-only"]] = "read-only"

#: What :attr:`FabricHandle.lease_mechanism` reports for a read-only boot (FW-2).
READ_ONLY_LEASE_MECHANISM: Final[str] = (
    "none: a read-only boot mints no writer and takes no writer lease"
)


class ReadOnlyFabricRefused(RuntimeError):
    """A write was attempted through a read-only boot's worker (FW-2, whole-branch review I-1; ``D-IMPL-374``).

    ``boot(..., read_only=True)`` mints no writer: the worker it hands back is
    L2 over a writer that refuses every write, by this name, before anything
    reaches the store. A read-only fabric exists to READ — replay beside the
    live writer foremost — and a write through it would be a second writer
    the single-writer invariant (whitepaper §7.3, INV-CH7-10) forbids.
    """


class _ReadOnlyWriter:
    """The writer a read-only boot's L2 holds: every write refused by name (FW-2).

    Structurally a :class:`~ccf.graph.protocols.GraphWriter`, so the worker is
    the same :class:`~ccf.assembly.worker.AssemblyWorker` a writer boot builds
    — the :class:`FabricHandle` contract is unchanged — but it holds no store,
    no boot token and no lease. It is private to this module and unreachable
    from the handle.
    """

    def _refuse(self, verb: str) -> NoReturn:
        raise ReadOnlyFabricRefused(
            f"{verb} refused: this fabric was booted read-only — it minted no"
            " writer and holds no writer lease, so it writes no graph content"
            " (FW-2; D-IMPL-374; whitepaper §7.3, INV-CH7-10)"
        )

    def upsert_entity(
        self, *, tenant_id: str, claim: EntityClaim, policy_bundle_version: str
    ) -> UpsertResult:
        """Refuse: a read-only fabric writes no graph content.

        Raises:
            ReadOnlyFabricRefused: always.
        """
        self._refuse("upsert_entity")

    def upsert_relationship(
        self, *, tenant_id: str, claim: RelationshipClaim, policy_bundle_version: str
    ) -> UpsertResult:
        """Refuse: a read-only fabric writes no graph content.

        Raises:
            ReadOnlyFabricRefused: always.
        """
        self._refuse("upsert_relationship")

    def close(self) -> None:
        """Nothing to retire: this writer was never minted and holds no graph."""


class FabricHandle:
    """What a booted fabric hands back: read access, L2, Control Plane, pin.

    Deliberately *not* a container for everything that was constructed. The
    write handle exists inside the worker and is unreachable from here, so
    "get the writer off the handle" is not a thing a caller can discover
    (DESIGN.md §2A.5.3 layer 2).

    :attr:`adapter` is a departure worth naming rather than slipping in. Until
    D-IMPL-93 this class carried capabilities and no *state* a caller could
    misuse; the pin makes it carry a fact. The fact is one an adopter needs:
    from D-IMPL-93 onward the adapter behind the graph seam can be third-party
    code, so *which* adapter answered, at *which* version, and under which
    credential references is part of what produced the answer. Whitepaper
    §7.10.1 dimension 2 is where it lands; a later plan threads it there.

    Attributes:
        reader: Read access to the graph.
        worker: L2 — the one holder of the write handle.
        registry: The Control Plane the fabric resolved its bindings from.
        adapter: The replay pin for the adapter that answered this boot. Three
            fields, none of which can hold a credential: a name, a version, and
            the *names* of the references the credentials came from.
        lease_scope: The scope of the writer lease this fabric's writer
            holds (SEC-013-C-03, D-IMPL-374 (1)), read off the boot token:
            ``"cross-process"`` when a substrate or declared lease excludes
            other processes, ``"process"`` when only this process's live-writer
            table does. :data:`READ_ONLY_LEASE_SCOPE` (``"read-only"``) for a
            read-only boot, which minted no writer and holds no lease (FW-2).
            ``None`` only for a handle built without a boot.
        lease_mechanism: Which lease that is, credential-free (the lease
            kind and the resource it is keyed on, for example the lock file a
            network store's declared lease holds), read off the boot token;
            :data:`READ_ONLY_LEASE_MECHANISM` for a read-only boot (FW-2).
            Deliberately not part of :attr:`adapter`, so the replay pin is
            unchanged; and neither name contains "writ", so the handle still
            offers nothing a caller could mistake for a write path.

    A read-only handle (``boot(..., read_only=True)``; FW-2, ``D-IMPL-374``)
    keeps this exact shape: :attr:`worker` is L2 over a writer that refuses
    every write by name (:class:`ReadOnlyFabricRefused`), and :meth:`close`
    closes the store only — there is no writer to retire and no lease to give
    back.
    """

    def __init__(
        self,
        *,
        reader: GraphReader,
        worker: AssemblyWorker,
        registry: ControlPlaneProtocol,
        adapter: AdapterPin,
        shutdown: Callable[[], None],
        lease_scope: WriterLeaseScope | Literal["read-only"] | None = None,
        lease_mechanism: str | None = None,
    ) -> None:
        self.reader = reader
        self.worker = worker
        self.registry = registry
        self.adapter = adapter
        self.lease_scope = lease_scope
        self.lease_mechanism = lease_mechanism
        self._shutdown = shutdown
        self._closed = False

    def close(self) -> None:
        """Retire the fabric: the writer stops accepting writes, the store closes.

        Releases the graph for a subsequent boot. This is orderly shutdown, not
        a way to hold two live writers — the retired writer refuses every
        further call.

        **Idempotent, and guarded here rather than relied on below** (review
        finding WR-07). This method is public and this class is also a context
        manager, so ``with handle:`` around a body that also closes is two
        calls written by someone doing nothing wrong — and the second one used
        to reach the adapter's store. Every in-tree store happens to tolerate
        it; :class:`ccf.graph.registry.BackendStore` now *requires* it of a
        third-party store, and requiring something is a poor reason to keep
        depending on it in the one place that can simply not do it twice.

        **Idempotent on success, retryable on failure** (review finding F6).
        The flag used to be set *before* the shutdown ran, so a shutdown that
        raised could never be retried: the second call returned immediately and
        the graph stayed marked as written-to. Setting it after means a
        successful close is still exactly one shutdown — the property the
        paragraph above argues for — while a failed one leaves the handle in
        the state it was actually in. Retrying re-runs the whole closure, which
        is safe because both steps it drives are required to be idempotent:
        :meth:`ccf.graph.protocols.GraphWriter.close` and
        :meth:`ccf.graph.registry.BackendStore.close`.
        """
        if self._closed:
            return
        self._shutdown()
        self._closed = True

    def __enter__(self) -> FabricHandle:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def _refuse_undeclared_secrets(
    adapter_name: str,
    declared: frozenset[str],
    supplied: Mapping[str, ResolvedSecret],
) -> None:
    """Refuse a credential offered for a field this adapter never declares.

    The survival of one of the four refusals the branch cascade performed: a
    credential supplied for a backend that was not selected. Selection is now a
    name, so the same mistake arrives as a credential keyed by a field the
    resolved adapter does not declare — and dropping it silently is WR-02's
    failure class, an argument the caller supplied that the machinery ignores.

    Built from key names only. No value is read, so nothing here needs the
    sanitizing :func:`ccf.graph.registry.validate_connection` performs, and the
    message reads in the same shape that one does: adapter, then field.

    **It also performs the reconciliation** :class:`ResolvedSecret` says it
    exists for (review finding WR-09). That class justifies itself on the two
    facts travelling together — "a pin cannot record a reference the value did
    not come from and no caller has to keep two mappings in step" — but the
    mapping *key* is what selects the config field here, and nothing read
    ``secret.field`` at all. A direct caller could pass a credential keyed by
    one field whose own record named another, and the mismatch was accepted in
    silence: the store got one field and the pin recorded a reference resolved
    for a different one. The manifest path happened to keep them in step
    because :func:`ccf.deployment.manifest._resolve_secret_references` writes
    both from one source — but that is the caller being careful rather than the
    contract holding, and ``boot`` is public and documented for direct use.
    """
    undeclared = sorted(set(supplied) - set(declared))
    if undeclared:
        known = ", ".join(sorted(declared)) if declared else "none"
        lines = [
            f"  {field} — not a credential field of this adapter"
            for field in undeclared
        ]
        raise ValueError(
            "\n".join(
                [
                    f"backend {adapter_name!r}: credentials were supplied for"
                    " fields it does not declare:",
                    *lines,
                    f"  declared credential fields: {known}",
                ]
            )
        )

    disagreeing = sorted(
        key for key, secret in supplied.items() if secret.field != key
    )
    if disagreeing:
        lines = [
            f"  {key} — its own record names the field {supplied[key].field!r}"
            for key in disagreeing
        ]
        raise ValueError(
            "\n".join(
                [
                    f"backend {adapter_name!r}: a resolved credential is keyed"
                    " by a field its own record does not name:",
                    *lines,
                    "  The key and the record's `field` are one fact. A caller"
                    " that can desynchronize them is the two-parallel-mappings"
                    " problem ResolvedSecret exists to remove — the store would"
                    " receive one field while the replay pin recorded a"
                    " reference resolved for another.",
                ]
            )
        )


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _mint_invalidation_register(
    registry: ControlPlaneProtocol, *, tenant_id: str
) -> Authorized[CompositionRegister]:
    """The composition recipe, for one tenant's invalidation register (D-IMPL-354).

    This module is a composition root — the one place the fabric's own
    writes obtain authority — and this is the whole of how it does so: the
    decision to let THIS fabric move ``tenant_id``'s invalidation boundary is
    recorded on the Control Plane's own audit log as a ``composition`` event,
    and the capability is minted with that event's content address as its
    ``decision_id``. One key, one tenant, one capability; nothing here is a
    wildcard and nothing here can be widened.
    """
    key = register_key(tenant_id)
    event = registry.audit_log.append(
        action="composition",
        key=key,
        version=CompositionRegister.action_id,
        resolved=True,
        occurred_at=_utc_now(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        CompositionRegister,
        tenant=tenant_id,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def _composed_tenants(tenant_ids: Sequence[str]) -> tuple[str, ...]:
    """The tenants this boot composes for: non-empty, distinct, each a real id."""
    if not tenant_ids:
        raise ValueError(
            "tenant_ids is empty: a fabric is composed for at least one tenant,"
            " because the composition root mints — per tenant — the Register"
            " capability under which a supersession moves that tenant's"
            " invalidation boundary; a fabric composed for nobody could record"
            " no supersession (D-IMPL-334; D-IMPL-354)"
        )
    seen: list[str] = []
    for tenant_id in tenant_ids:
        if not isinstance(tenant_id, str) or not tenant_id or tenant_id != tenant_id.strip():
            raise ValueError(
                f"tenant_ids contains {tenant_id!r}, which is not a tenant id"
            )
        if tenant_id in seen:
            raise ValueError(
                f"tenant_ids names {tenant_id!r} twice; a composition mints one"
                " capability per tenant, and a repeated tenant is a mistake"
                " rather than a second grant"
            )
        seen.append(tenant_id)
    return tuple(seen)


def boot(
    *,
    backend: str,
    connection: Mapping[str, object] | None = None,
    secrets: Mapping[str, ResolvedSecret] | None = None,
    registry: ControlPlaneProtocol,
    resolution_spec_key: str,
    resolution_spec_version: str,
    policy_bundle_key: str,
    policy_bundle_version: str,
    tenant_ids: Sequence[str],
    read_only: bool = False,
) -> FabricHandle:
    """Construct a fabric over one graph and return its handle.

    Selection is a *name*, resolved through :mod:`ccf.graph.registry`. This
    function knows of no adapter in particular: it resolves the one it was
    given, validates the connection mapping against the contract that adapter
    declares, and calls the two factories that adapter registered. Adding a
    substrate therefore costs no edit here, which is the whole of D-IMPL-93
    property (2).

    ``backend`` is required and has no default, and that is a refusal rather
    than an omission. A fabric that could infer its own substrate could boot
    against a development store in production and still pass every test. The
    fabric does not infer, and it does not fall back.

    Only the named adapter is imported. An adapter whose driver is an optional
    extra therefore loads its driver only when a deployment asks for that
    adapter — a property that used to be two hand-written lazy branches here
    and now holds by construction, because resolution imports exactly one write
    module. How an adapter arranges its own imports is that adapter's recorded
    decision, made in its own module and argued there; nothing here flattens
    the shapes into one.

    Every Control Plane binding is an explicit, pinned ``(key, version)`` pair.
    There are no defaults and no "latest": a fabric whose configuration could
    drift between boots is a fabric whose decisions cannot be replayed
    (D-IMPL-38, whitepaper §7.10).

    **Where the branch cascade's four refusals went**, so a reader can see that
    nothing was dropped when it was deleted:

    1. *Not exactly one backend selected* — structurally impossible now. One
       name selects one adapter.
    2. *A credential supplied for a backend that was not selected* — the
       ``secrets`` membership check below, against the resolved adapter's own
       declared credential fields.
    3. *A required connection setting missing* — the adapter's config model,
       where the field is required (D-07).
    4. *A connection setting the adapter does not take* — the same model, by
       the ``extra="forbid"`` every adapter contract inherits.

    Refusals 3 and 4 are built by
    :func:`ccf.graph.registry.validate_connection` and nowhere else. A second
    wrapper written here would format the underlying validation error, and that
    rendering embeds the value that was supplied.

    **The writer lease and the classification authority** (SEC-013 and
    SEC-023; ``D-IMPL-374``). A writer boot's mint takes the store's writer
    lease (:func:`ccf.graph._writer.mint_boot_token`), so a second writer of
    one graph is refused whether it boots in this process or — under a
    cross-process lease — in another, and a persistent network store that
    declares no lease refuses the mint. The handle's reader is the store's
    own reader governed by the
    :class:`~ccf.graph.protocols.ClassificationAuthority` minted here, from
    the pinned resolution spec its L2 enforces — the only place that
    authority is minted — so every view it returns is stamped and every
    classification query it answers carries it. Every step after the mint runs
    inside one guard that retires the writer and gives back its lease on
    failure (PM10, panel C10), so a corrected retry boots.

    Args:
        backend: The adapter name this fabric boots against. Required; resolved
            through :func:`ccf.graph.registry.resolve`, which refuses a name no
            installed adapter registers and lists the ones that are registered.
        connection: The adapter's connection settings, validated against the
            contract it declares. Keys and their meaning are the adapter's, not
            this function's. Environment-supplied: never persisted, and never
            reproduced in the graph identity the single-writer check uses.
        secrets: Resolved credentials keyed by the adapter's config field, each
            carrying the *name* of the reference it came from. The reference
            name is what reaches :attr:`FabricHandle.adapter`; the value goes
            to the adapter's store factory and nowhere else. A key the adapter
            does not declare as a credential field is refused.
        registry: Control Plane the resolution spec and policy bundle come from.
        resolution_spec_key: Key of the :class:`EntityResolutionSpec` artifact.
        resolution_spec_version: Pinned version of that artifact.
        policy_bundle_key: Key of the policy bundle in force.
        policy_bundle_version: Pinned version of that bundle.
        tenant_ids: The tenants this fabric is composed for. Required and
            non-empty, with no default (D-IMPL-354): for each, this
            composition root mints — through the recipe, audited on
            ``registry.audit_log`` — the one ``Register`` capability under
            which a supersession moves that tenant's invalidation boundary
            (``D-IMPL-334``), and hands them to the writer's
            :class:`~ccf.controlplane.invalidation.ControlPlaneInvalidationSink`.
            A supersession under a tenant not named here is refused by the
            sink, typed, at the write — never filed under a fallback.
            A manifest-driven deployment passes its one resolved tenant.
        read_only: ``True`` boots the fabric READ-ONLY (FW-2, whole-branch
            review I-1; ``D-IMPL-374``): the store is opened and its reader is
            governed exactly as a writer boot governs it — every view stamped
            with the :class:`~ccf.graph.protocols.ClassificationAuthority`
            minted from the pinned resolution spec through the same private
            mint path — but no boot token is minted, so no writer exists, no
            writer lease is taken and the graph is not marked live; a writer
            boot of the same graph, here or in another process, is unaffected
            by it, and it is unaffected by one. The handle's worker refuses
            every write by name (:class:`ReadOnlyFabricRefused`), no
            invalidation-register capability is minted (nothing can supersede),
            :attr:`FabricHandle.lease_scope` reports
            :data:`READ_ONLY_LEASE_SCOPE` and :meth:`FabricHandle.close` closes
            the store only. It writes no graph content, but it is not
            write-free at the substrate (N-6): opening the store still runs
            the store's own open-time setup, as at a writer boot (schema
            creation; a Fluree ledger's creation). This is the reader
            Decision Replay uses beside a live writer
            (:class:`~ccf.replay.environment.RecordedEnvironment`).
            ``False`` (the default) is the writer boot every earlier caller
            gets, unchanged. Whether a WRITER boot takes a lease stays the
            store's declaration, never the caller's (SEC-013): this flag does
            not skip a lease, it declines the writer the lease exists for.
            Because it takes none, a read-only boot sets the connection's
            writer-lease setting (``writer_lease_lock_dir``) aside before
            validation, so that setting is neither validated nor handed to
            the store (N-2, ``D-IMPL-374``): an examiner on another host or
            under another account boots read-only with the deployment's
            settings unchanged.

    Raises:
        ValueError: ``tenant_ids`` is empty, repeats a tenant, or carries a
            value that is not a tenant id.
        ccf.graph.registry.UnknownBackend: no installed adapter registers
            ``backend``.
        ccf.graph.registry.InvalidBackendConfig: ``connection`` does not
            satisfy the resolved adapter's contract (for a read-only boot,
            once its writer-lease setting is set aside).
        ValueError: ``secrets`` names a field the resolved adapter does not
            declare as a credential field; or a supplied credential is keyed by
            a field its own record does not name; or discovery found a
            packaging conflict among the installed adapters; or the named
            adapter is installed but its declaration could not be loaded.
        ccf.graph._writer.SingleWriterViolation: a live writer already exists
            for this graph, in this process or, under a cross-process writer
            lease, in another (SEC-013; ``D-IMPL-374``) — a writer boot only;
            a read-only boot mints no writer and is never refused for one.
        ccf.graph.protocols.WriterLeaseRequired: the store is a persistent
            network store and declares no writer lease (SEC-013;
            ``D-IMPL-374``); a writer boot only.
        ccf.controlplane.registry.ControlPlaneMissing: a pinned key or version
            is not registered.
        TypeError: the resolution-spec artifact is not an
            :class:`EntityResolutionSpec`; or the resolved adapter's writer
            constructor was handed a store it does not write through; or that
            constructor returned an object that is not a ``BaseGraphWriter``
            and so could never release the graph on close
            (:func:`ccf.graph._writer.adopt_writer`); or the store offers no
            ``writer_lease()``, or a lease that declares no known scope
            (SEC-013).
        BaseException: whatever the resolved adapter's own store or writer
            constructor raises, re-raised unchanged. The adapter chooses the
            type — it is third-party code — so this function does not wrap it
            and does not name it. What it guarantees instead is that a boot
            which failed leaves nothing behind: the store is closed and the
            graph is released, so a corrected retry boots rather than being
            refused as a second writer.
    """
    composed = _composed_tenants(tenant_ids)
    record = resolve(backend)
    registration = record.registration
    settings: Mapping[str, object] = connection or {}
    if read_only:
        # N-2 (`D-IMPL-374`): a read-only boot takes no writer lease, so the
        # setting that declares one is neither validated nor handed to the store.
        settings = _without_lock_directory_setting(registration.config_model, settings)
    config = validate_connection(registration, settings)
    resolved_secrets = dict(secrets or {})
    _refuse_undeclared_secrets(
        registration.name, registration.secret_fields, resolved_secrets
    )
    # Unwrapped at the call site and nowhere earlier: a credential bound to a
    # local before it is needed is a value with a longer life than the call
    # that wanted it. The reference names stay behind, for the pin.
    store = registration.open_store(
        config,
        {field: secret.value for field, secret in resolved_secrets.items()},
    )
    adapter = AdapterPin(
        name=registration.name,
        version=record.version,
        secret_refs=tuple(
            sorted(secret.ref_name for secret in resolved_secrets.values())
        ),
    )
    if read_only:
        # FW-2 (`D-IMPL-374`): the reader, governed; no token, no writer, no lease.
        return _boot_read_only(
            store=store,
            registry=registry,
            adapter=adapter,
            resolution_spec_key=resolution_spec_key,
            resolution_spec_version=resolution_spec_version,
            policy_bundle_key=policy_bundle_key,
            policy_bundle_version=policy_bundle_version,
        )
    try:
        token = mint_boot_token(store=store)
    except BaseException:
        store.close()
        raise

    try:
        # `adopt_writer` refuses a returned object that is not a
        # `BaseGraphWriter` — the success-path half of the guard below (review
        # finding F6). Deliberately *inside* this `try`, so a refusal releases
        # the mint and closes the store on the same path a raising constructor
        # takes; both are "the adapter did not give us a writer".
        writer = adopt_writer(
            registration.make_writer(store, token), adapter=registration.name
        )
        # `D-IMPL-334`. The composition root binds the invalidation sink, not
        # the deployment: a supersession must report its boundary whether or
        # not anyone remembered to ask for it. Bound here rather than passed
        # to `make_writer` because that factory is adapter-supplied
        # (`D-IMPL-93`) and its signature is not this function's to change.
        attach = getattr(writer, "attach_invalidation_sink", None)
        if attach is not None:
            # D-IMPL-354: the sink is not a composition root and mints
            # nothing; this function is, and mints exactly one `Register` per
            # composed tenant — for that tenant's register key and no other.
            attach(
                ControlPlaneInvalidationSink(
                    registry=registry,
                    authorities=tuple(
                        _mint_invalidation_register(registry, tenant_id=tenant_id)
                        for tenant_id in composed
                    ),
                )
            )
    except BaseException:
        # The same guard the mint above gets, for the same reason, over a call
        # that needs it more: since D-IMPL-93 this constructor is a callable an
        # installed distribution supplied, and the composition root controls
        # neither what it does nor whether it returns. If it raises, the store's
        # connection is the only handle to it that ever existed and no caller
        # can reach it, and the graph is marked as having a writer that does not
        # exist — so a corrected retry would be refused as a second writer, the
        # outcome the comment below says must not happen. Order matters: release
        # the mint first, so a store whose `close` also raises cannot leave the
        # graph permanently unbootable on top of everything else.
        #
        # `try`/`finally` rather than two statements (close-review finding F4,
        # Gemini and Ollama independently). The ordering rationale above is
        # unchanged and still correct — it reasoned about `store.close()`
        # raising, which is the second step. What it did not reason about is the
        # *first* step raising: written as two statements, a `release_boot_token`
        # that raised skipped `store.close()` entirely and leaked the connection,
        # which is the leak this whole handler exists to prevent. Both steps run
        # now, in the same order, whatever either of them does.
        try:
            release_boot_token(token)
        finally:
            store.close()
        raise

    def shutdown() -> None:
        """Retire the writer, then the store — both, whatever the first does.

        Same shape and same finding (F4) as the handler above, for the same
        reason: written as two statements, a `writer.close()` that raised
        skipped `store.close()` and leaked the connection. `writer.close()` is
        also what releases the mint, so ordering it first is the rule the
        handler above states, not a coincidence.
        """
        try:
            writer.close()
        finally:
            store.close()

    # EVERY step after the mint is inside this guard (PM10, panel C10;
    # `D-IMPL-374`): the worker build, the SEC-023 authority wrap and the
    # handle itself. A half-booted fabric must not leave the graph marked as
    # written-to — nor, since SEC-013, its cross-process writer lease held —
    # or a corrected retry, here or in another process, would be refused as a
    # second writer. The panel measured both stranded when the guard covered
    # the worker build alone.
    try:
        spec = _resolution_spec(
            registry, resolution_spec_key, resolution_spec_version
        )
        worker = AssemblyWorker(
            writer=writer,
            resolution=SpecDrivenEntityResolution(spec=spec),
            registry=registry,
            policy_bundle_key=policy_bundle_key,
            policy_bundle_version=policy_bundle_version,
        )

        # SEC-023 (`D-IMPL-374` ruling (3) (a)): the reader a booted fabric
        # hands out stamps every view with the authority its L2 enforces, and
        # refuses a classification query that authority does not cover.
        # Imported here so the module's line anchors other records cite stay
        # where they were.
        from ccf.graph.governed_reader import governed_reader

        return FabricHandle(
            reader=governed_reader(store.reader, _mint_authority_of(spec)),
            worker=worker,
            registry=registry,
            # Reference names, never the fields they filled and never a value.
            # Reading the field names instead would pin "a credential was used"
            # where D-08 asks which one.
            adapter=adapter,
            shutdown=shutdown,
            lease_scope=token.lease_scope,
            lease_mechanism=token.lease_mechanism,
        )
    except BaseException:
        shutdown()
        raise


def _resolution_spec(
    registry: ControlPlaneProtocol, key: str, version: str
) -> EntityResolutionSpec:
    """The pinned resolution spec, or a refusal naming what is registered instead."""
    spec = registry.resolve(key, version)
    if not isinstance(spec, EntityResolutionSpec):
        raise TypeError(
            f"artifact at ({key!r}, "
            f"{version!r}) is "
            f"{type(spec).__name__}, not EntityResolutionSpec"
        )
    return spec


def _boot_read_only(
    *,
    store: BackendStore,
    registry: ControlPlaneProtocol,
    adapter: AdapterPin,
    resolution_spec_key: str,
    resolution_spec_version: str,
    policy_bundle_key: str,
    policy_bundle_version: str,
) -> FabricHandle:
    """The read-only half of :func:`boot` (FW-2, whole-branch review I-1; ``D-IMPL-374``).

    Everything a writer boot does to GOVERN the reader, and nothing it does to
    WRITE graph content. The ``store`` the caller opened has already run its
    own open-time setup (schema creation; a Fluree ledger's creation), exactly
    as for a writer boot; this function neither prevents nor undoes it (N-6).
    The pinned spec is resolved and type-checked, L2 is built over it
    (so the policy-bundle pin is validated and audited exactly as at a writer
    boot), and the classification authority is minted from that spec by
    :func:`_mint_authority_of` — the one private mint path both boots share,
    so a read-only view's stamp is the same boot-minted attestation a writer
    boot's is. No :func:`~ccf.graph._writer.mint_boot_token` call: no writer,
    no lease, no live-writer mark. A failure closes the store it opened.
    """
    try:
        spec = _resolution_spec(
            registry, resolution_spec_key, resolution_spec_version
        )
        worker = AssemblyWorker(
            writer=_ReadOnlyWriter(),
            resolution=SpecDrivenEntityResolution(spec=spec),
            registry=registry,
            policy_bundle_key=policy_bundle_key,
            policy_bundle_version=policy_bundle_version,
        )

        from ccf.graph.governed_reader import governed_reader

        return FabricHandle(
            reader=governed_reader(store.reader, _mint_authority_of(spec)),
            worker=worker,
            registry=registry,
            adapter=adapter,
            shutdown=store.close,
            lease_scope=READ_ONLY_LEASE_SCOPE,
            lease_mechanism=READ_ONLY_LEASE_MECHANISM,
        )
    except BaseException:
        store.close()
        raise


def _mint_authority_of(spec: EntityResolutionSpec) -> ClassificationAuthority:
    """Mint the classification authority of the spec this fabric's L2 enforces.

    SEC-023 (``D-IMPL-374`` fix round 1, I-1 (b)). The composition root is the
    one place that mints: the spec here is the one
    :class:`~ccf.assembly.worker.AssemblyWorker` was just built over, and the
    mint carries its content address, so the stamp on every view this fabric
    reads is an attestation of what L2 enforces, not a caller's declaration.
    """
    from ccf.graph.protocols import _mint_classification_authority

    written: dict[str, set[str]] = {}
    for rule in spec.entity_rules:
        written.setdefault(rule.entity_class, set()).update(rule.attribute_keys)
    return _mint_classification_authority(
        spec_address=content_hash(spec),
        governed=spec.governed_attributes(),
        written={cls: frozenset(attrs) for cls, attrs in written.items()},
    )
