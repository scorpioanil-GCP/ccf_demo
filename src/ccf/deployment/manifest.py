"""One call from a manifest to a booted fabric — wiring, and nothing past wiring.

SDK-defined mechanism (CLAUDE.md §6.4 and §10). :func:`ccf.boot.boot` is already
well-shaped: every Control Plane binding is an explicit, pinned ``(key, version)``
pair, there are no defaults and no "latest", because a fabric whose configuration
drifts between boots cannot be replayed (D-IMPL-38, whitepaper §7.10). Its
contract is preserved here verbatim — this module changes what *produces* the
pins, never what ``boot`` requires of them. ``boot`` remains directly callable
and every existing call site keeps working (D-14 is additive).

Why the manifest enumerates
---------------------------

The set of Control Plane artifacts in force is dimension 2 of the
five-dimension Decision Replay record (whitepaper §7.10.1). A glob would make
that set a function of directory contents at boot time, with **no artifact
recording that a dropped-in file changed what was in force** — so
:class:`~ccf.controlplane.artifacts.ManifestEntry` refuses a pattern at parse
and the manifest names every file.

The same argument runs one step further. A path that *leaves* the manifest's
directory makes the set a function of the filesystem outside the deployment,
which is strictly worse than a glob: the dropped-in file does not even have to
be dropped in. So the paths a manifest names are enumerated **and** contained —
the contract refuses an absolute path or a ``..`` segment from the string, and
:func:`_document_inside_the_deployment` refuses whatever a symlink would have
reached. What is in force is the deployment's own tree.

The boundary this module must not cross
---------------------------------------

The governance risk an ergonomics entry point runs is growing past wiring. The
next obvious convenience — *and it also runs the operators* — would swallow the
projection engine's independently-resolved operator set and make lineage strict
equality (INV-CH7-47) compare a value against itself. The gate would stay green
and the invariant would be gone with no failing test to say so.

``tests/products/test_gate_independence.py`` and the ``cinv02-deployment-gates``
lint rule stand against exactly that, and this module does not weaken either.
:func:`load_and_boot`'s own docstring states the boundary in the negative, so
the line is legible from the surface rather than only from the guard.

Algorithmic module (CINV-03) — see the package docstring for why file I/O here
is not a contradiction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ccf.boot import FabricHandle, boot
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DEPLOYMENT_MANIFEST,
    DeploymentManifest,
    ManifestEntry,
    load_artifact,
)
from ccf.controlplane.registry import ControlPlaneProtocol, RegistrationRefusal
from ccf.deployment.classes import (
    refuse_registration_the_sdk_fixes,
    refuse_role_the_sdk_fixes,
    resolve_artifact_class,
)
from ccf.deployment.pins import ArtifactPin, ResolvedPins

__ccf_mode__ = "algorithmic"

__all__ = ["BootedFabric", "load_and_boot"]


@dataclass(frozen=True)
class BootedFabric:
    """What :func:`load_and_boot` hands back: the fabric, its pins, its artifacts.

    A frozen dataclass rather than a :class:`~ccf.contracts.base.CCFContract`,
    for the reason :class:`~ccf.controlplane.artifact_base.ArtifactClass`
    records: it carries a live handle, which has no canonical serialization and
    never belongs in a content hash.

    Attributes:
        handle: The booted fabric, exactly as :func:`ccf.boot.boot` returns it —
            reader, worker, Control Plane, and **no writer**.
        pins: The record of what was put in force: ``role: register`` entries
            only.
        tenant_id: The resolved tenant, from the manifest or from the caller.
        artifacts: Every parsed artifact, keyed by manifest key, **both roles**.

            This is D-IMPL-80's return path. The ruling requires ``role: load``
            entries to come back to the caller rather than being registered;
            returning the ``register``-role ones alongside them costs nothing
            and closes a second gap. Without it, an adopter needing the parsed
            operator-parameters artifacts to hand to a registry builder would
            re-read them off disk or ``isinstance``-filter them out of the
            Control Plane — and that filtering idiom, copied across nine
            examples, is a new duplication class of exactly the sort this phase
            exists to remove. With it the adopter writes
            ``{key: booted.artifacts[key] for key in (...)}``, naming its own
            manifest keys: explicit deployment configuration rather than type
            introspection.

            **What this does not weaken.** ``role`` governs registration and
            pinning, never visibility. A ``role: load`` artifact appearing here
            is still absent from ``pins``, still absent from the Control Plane
            registry, and still absent from replay dimension 2. ``artifacts`` is
            a parse result handed back to the caller; ``pins`` is the record of
            what was put in force.
        survivor_cap: The manifest's D-10 cap value, verbatim (15.2-08). The
            governed route from Control Plane configuration to the engine:
            the adopter passes this to
            :class:`~ccf.projection.engine.ProjectionEngine`'s
            ``survivor_cap`` at construction — value-threading only, exactly
            as ``tenant_id`` travels; this module still constructs no engine
            (the D-IMPL-86 correction's boundary). Direct :func:`ccf.boot.boot`
            callers pass the value to the engine themselves. ``None`` = no
            cap configured, the engine's own default.
    """

    handle: FabricHandle
    pins: ResolvedPins
    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    survivor_cap: int | None


def _resolve_tenant(manifest: DeploymentManifest, supplied: str | None) -> str:
    """Return the one tenant this deployment runs as, or refuse.

    Exactly one source may supply it. Both-absent and a conflicting pair are
    both refused rather than resolved by precedence, mirroring
    ``_open_backend``'s refuse-to-infer posture: a deployment whose tenant
    depends on which source won is a deployment whose graph scope nobody wrote
    down (INV-CH7-16, D-IMPL-05).
    """
    if manifest.tenant_id is None and supplied is None:
        raise ValueError(
            "no tenant_id: the manifest declares none and none was supplied;"
            " state it in exactly one of the two places"
        )
    if (
        manifest.tenant_id is not None
        and supplied is not None
        and manifest.tenant_id != supplied
    ):
        raise ValueError(
            f"tenant_id conflict: the manifest declares"
            f" {manifest.tenant_id!r} and {supplied!r} was supplied; the fabric"
            " does not choose between them — remove one"
        )
    resolved = manifest.tenant_id if manifest.tenant_id is not None else supplied
    assert resolved is not None  # narrowed by the both-absent refusal above
    return resolved


def _document_inside_the_deployment(root: Path, entry: ManifestEntry) -> Path:
    """Resolve ``entry.path`` under ``root``, or refuse it for leaving.

    The read half of the two-part path refusal
    :attr:`~ccf.controlplane.artifacts.ManifestEntry.path` describes.
    :meth:`~ccf.controlplane.artifacts.ManifestEntry._path_stays_beside_the_manifest`
    has already refused absolute paths and ``..`` segments at parse; what
    survives to here is a plain relative name, and a plain relative name can
    still be a **symlink pointing out of the deployment**. No inspection of the
    string can see that, so it is asked of the filesystem: both sides are
    ``resolve()``\\ d — which normalizes *and* follows links — and the result
    must lie under the manifest's own directory.

    The two checks are not one check written twice. The contract answers *is
    this a well-formed declaration*, from the string, for every consumer of
    :class:`~ccf.controlplane.artifacts.ManifestEntry`. This answers *does this
    open a file inside the deployment*, against a root only the caller knows.
    Deleting either leaves a real hole: without the contract check an adopter
    constructing a manifest by hand gets no refusal at all; without this one a
    symlink defeats the contract check completely.

    **Refused, never followed and never rewritten.** The posture is
    :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes`'s: a
    governance mechanism refuses rather than repairs, because silently
    substituting a corrected path would leave the manifest saying one thing and
    the deployment doing another, and the manifest is the document the audit
    plane reads back. A deployment that genuinely needs a document from
    elsewhere copies it in — where it is versioned with the rest of the
    artifact set — rather than linking to a file the manifest's content hash
    cannot see.

    A symlink whose target is *inside* the deployment is admitted, deliberately:
    it resolves under the root, so the artifact set is still the deployment's
    own tree.

    Raises:
        ValueError: the entry resolves outside ``root``. The message names the
            resolved path, because a refusal an operator cannot locate is a
            refusal they will route around; it never names the file's
            **contents**, which is the disclosure this whole check exists to
            stop.
    """
    anchor = root.resolve()
    resolved = (anchor / entry.path).resolve()
    if not resolved.is_relative_to(anchor):
        raise ValueError(
            f"manifest key {entry.key!r} names path {entry.path!r}, which"
            f" resolves to {resolved} — outside {anchor}, the manifest's own"
            " directory. The path is a plain name, so what leaves the"
            " deployment is a symlink along it. A manifest names files beside"
            " itself: what is in force is the deployment's own tree, not"
            " whatever that tree points at, and a `role: register` entry would"
            " content-hash the far end into Decision Replay dimension 2. Copy"
            " the document into the deployment, or name one already there."
        )
    return resolved


def _preflight_backend(
    manifest: DeploymentManifest,
    *,
    database_path: str | None,
    postgres_dsn: str | None,
    neo4j_uri: str | None,
) -> None:
    """Refuse a backend declaration the environment cannot satisfy (D-08).

    **This runs before any artifact is parsed and before anything is
    registered**, and the ordering is the whole point. A manifest declaring
    ``postgres`` with no DSN supplied parses perfectly well, so a check placed
    beside the ``boot`` call at the end would register every artifact first and
    fail afterwards — leaving Control Plane state from a fabric that never
    booted. That is a replay-integrity problem, not an untidiness: the registry
    would then answer "what was in force" for a deployment that never ran.

    The refusal is loud and there is **no fallback to SQLite**. A fabric that
    guessed its substrate could boot against a development file in production
    and still pass every test — the reason ``_open_backend`` refuses to infer,
    inherited here rather than re-decided.

    A declared ``memory`` backend (Phase 15.2 D-06) needs no connection
    argument — there is nothing to connect to — so for it the check runs the
    other way only: supplying ``database_path``, ``postgres_dsn``, or
    ``neo4j_uri`` alongside a ``memory`` declaration is refused as a
    contradiction, exactly as supplying the other backend's argument is. A
    declared ``neo4j`` backend (plan 15.2-12) requires ``neo4j_uri``, the
    environment-supplied mirror of ``postgres_dsn``.

    Raises:
        ValueError: the declared backend's connection argument is missing, or
            an argument the declared backend does not take was supplied.
    """
    supplied = {
        "database_path": database_path,
        "postgres_dsn": postgres_dsn,
        "neo4j_uri": neo4j_uri,
    }
    required = {
        "sqlite": "database_path",
        "postgres": "postgres_dsn",
        "memory": None,
        "neo4j": "neo4j_uri",
    }[manifest.backend]
    declared = manifest.backend
    if required is not None and supplied[required] is None:
        raise ValueError(
            f"the manifest declares backend {declared!r} and no"
            f" {required} was supplied; the fabric does not guess a"
            " substrate and does not fall back"
        )
    for argument, value in supplied.items():
        if argument != required and value is not None:
            raise ValueError(
                f"the manifest declares backend {declared!r} but"
                f" {argument} was also supplied; supply only the argument"
                " the manifest's declared backend needs"
            )


def load_and_boot(
    manifest_path: str | Path,
    *,
    registry: ControlPlaneProtocol,
    database_path: str | None = None,
    postgres_dsn: str | None = None,
    neo4j_uri: str | None = None,
    tenant_id: str | None = None,
) -> BootedFabric:
    """Load a manifest, validate and register what it names, and boot the fabric.

    Replaces the hand-written registration prologue that preceded every
    :func:`ccf.boot.boot` call with one call over one content-hashable document.

    What this call does, in order:

    1. Parses the manifest through
       :func:`~ccf.controlplane.artifacts.load_artifact` — never
       PyYAML's plain safe loader, because the artifact loader is what
       suppresses the
       timestamp resolver (D-02) and refuses floats and zone-less timestamps.
    2. **Preflights** the tenant, the D-IMPL-80 role and the D-IMPL-85
       registration path of every entry, **that every entry's document actually
       lies inside the deployment**, and the declared backend against the
       supplied connection argument — all before any document is read and
       before anything is registered.
    3. Parses **every** entry, then registers the ``role: register`` ones
       **through the path each entry's** ``registration`` **declares** —
       :meth:`register_typed
       <ccf.controlplane.registry.ControlPlaneRegistry.register_typed>` or
       :meth:`register_versioned
       <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>` with
       its D-05 bump check (D-IMPL-85). Two phases, deliberately: a malformed
       document at entry seven would otherwise leave entries one through six
       registered, which is partial Control Plane state produced by a deployment
       that never booted.
    4. Calls :func:`ccf.boot.boot` with the pins it just collected.

    What this call does **not** do — the abstraction line, stated on the surface
    rather than only in the guard: it does not execute operators, does not
    project, does not build a Context Product, does not run the three validation
    gates, and does not construct a product's lineage record. The adopter reads
    ``pins`` and passes them to ``build_replay_record`` itself, because D-06
    requires that line to stay in adopter code — the moment the SDK selects which
    bindings are in force, dimension 2 of the replay record is assembled by a
    rule nobody in the deployment wrote down.

    What is **still not guaranteed**, stated rather than papered over: a failure
    *inside* the registration loop — a backend error, say — can still leave
    earlier entries registered. That is accepted. Registration is
    content-addressed and audited, so a corrected re-run registers identical
    content to identical versions and the audit log shows both attempts. There
    is deliberately no rollback: a Control Plane that silently un-registers is
    worse than one that records a retry.

    The day-1 shape of what follows this call, so the spine is written down
    where the call is: the adopter ingests from
    ``booted.artifacts[<signal-batch-key>].envelopes`` through
    ``booted.handle.worker``, builds a view from ``booted.handle.reader``,
    assembles the ``parameters`` mapping for the operator-registry builder by
    naming its own manifest keys against ``booted.artifacts``, and mints the
    MAX_TTL registration and the product-class registration itself. That last
    part is deliberate: the TTL pin must stay an independently authored
    registration, or Gate 3 compares a ceiling against itself.

    **Handle lifecycle.** The returned ``handle`` owns a backend connection, and
    its disposal contract is unchanged from :func:`ccf.boot.boot`:
    :meth:`ccf.boot.FabricHandle.close` retires the writer and closes the store,
    and the handle is a context manager, so ``with booted.handle:`` is the
    ordinary shape. What changes here is not the contract but how cheap it is to
    acquire a handle absentmindedly — one call is easy to put in a loop over
    manifests, over tenants, or over test cases, and a loop that never closes
    leaks one connection per iteration and will eventually be refused a boot by
    the single-writer check. Close each handle before booting the next.

    Args:
        manifest_path: The manifest document. Every entry's ``path`` resolves
            relative to **this file's own directory**, never the process's
            working directory — a deployment's artifact set must not depend on
            where a script was launched from — and **cannot leave it**.

            The second clause is enforced, not merely stated, and by two
            checks rather than one because one cannot cover both cases.
            :class:`~ccf.controlplane.artifacts.ManifestEntry` refuses an
            absolute path or a ``..`` segment at parse, from the string alone;
            :func:`_document_inside_the_deployment` resolves each entry against
            this file's directory and refuses anything landing outside it,
            which is what closes a plain name that is a symlink out. A
            manifest is trusted no further than D-IMPL-84 already trusts it —
            the whole ``ccf.`` namespace is reserved precisely because a
            manifest can be authored to squat an SDK class id — and a document
            trusted that little does not get to name ``/``-rooted paths. An
            entry that escaped would put arbitrary file contents on
            ``BootedFabric.artifacts`` and, on ``role: register``,
            content-hash them into Decision Replay dimension 2.
        registry: The Control Plane to register into. A caller argument, never
            constructed here: a registry built behind the adopter's back would
            split the audit sequence in two, and the Control Plane is the audit
            plane, singular (whitepaper §7.8.2).
        database_path: SQLite file, when the manifest declares ``sqlite``.
        postgres_dsn: libpq connection string, when the manifest declares
            ``postgres``. From the environment; never persisted, and never in
            the manifest.
        neo4j_uri: Bolt connection URI, when the manifest declares ``neo4j``
            (plan 15.2-12). Same posture as ``postgres_dsn``: from the
            environment, never persisted, never in the manifest — a Bolt URI
            can carry credentials, and the manifest is a content-hashed audit
            artifact (threat T-15.2-05).
        tenant_id: The deployment's tenant, when the manifest does not name it.

    Raises:
        ValueError: the tenant is absent from both sources or conflicts between
            them; the declared backend's connection argument is missing or the
            wrong one was supplied; an entry's ``path`` resolves outside the
            manifest's own directory — refused in preflight, before any
            document is opened, and never followed; an entry declares a role
            the SDK fixes otherwise (D-IMPL-80); an entry declares a
            registration path its
            class's own contract contradicts (D-IMPL-85 — an author-versioned
            class declared ``typed``, or a typed-only class declared
            ``versioned``); an entry names a ``ccf.``-prefixed class id the SDK
            does not ship, which is refused rather than resolved to the open
            envelope because the envelope would let arbitrary content register
            and pin under an SDK class name (D-IMPL-84); or a
            ``registration: versioned`` entry was
            refused by the D-05 hash-verified bump check. That last one is a
            **returned** refusal from :meth:`register_versioned
            <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>`
            turned into a loud failure here, naming the key, the class and the
            refusal type: a refusal is never swallowed, never downgraded to a
            warning, and never retried down the ``typed`` path.
        TypeError: a ``registration: versioned`` entry names a class whose
            documents declare no string ``artifact_version``, so the bump check
            has nothing to verify. This is what an adopter sees when they declare
            ``versioned`` for a class that is not author-versioned; for the
            classes the SDK knows the answer for,
            :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes`
            refuses in preflight, before anything is read.
        ccf.controlplane.artifacts.ArtifactLoadError: the manifest or any
            artifact document is not valid YAML, or does not satisfy its
            declared class contract.
        OSError: the manifest or a named artifact document cannot be read.
    """
    manifest_file = Path(manifest_path)
    manifest = load_artifact(
        manifest_file.read_text(encoding="utf-8"), DEPLOYMENT_MANIFEST
    )
    assert isinstance(manifest, DeploymentManifest)  # DEPLOYMENT_MANIFEST's contract

    resolved_tenant = _resolve_tenant(manifest, tenant_id)
    root = manifest_file.parent
    document_paths: dict[str, Path] = {}
    for entry in manifest.artifacts:
        refuse_role_the_sdk_fixes(entry.class_id, entry.role)
        # Ordering is the point and it must stay here. This runs **before any
        # document is read** and before anything is registered, so a manifest
        # that would have routed an author-versioned class around the D-05 bump
        # check — or squatted an SDK class id — never reaches the parse phase.
        #
        # This is applied to EVERY entry, `role: load` included, and it is not
        # an oversight that a `load` entry is held to a registration path it
        # never travels. See `ManifestEntry.registration` for why the check is
        # class-wide rather than role-scoped; do not make it conditional on
        # `entry.role` without reading that first, because doing so changes the
        # refusal surface rather than tidying it.
        refuse_registration_the_sdk_fixes(entry.class_id, entry.registration)
        # Same ordering, same reason, one entry stronger: an entry that escapes
        # the deployment is refused before **any** document is opened, so a
        # manifest whose seventh entry symlinks out never reads its first six
        # either. The keys are unique by contract (`_keys_are_unique`), so this
        # mapping is total over the entries and phase one resolves nothing a
        # second time.
        document_paths[entry.key] = _document_inside_the_deployment(root, entry)
    _preflight_backend(
        manifest,
        database_path=database_path,
        postgres_dsn=postgres_dsn,
        neo4j_uri=neo4j_uri,
    )

    # Phase one: parse everything. Nothing is registered until every document in
    # the manifest has been read and validated.
    parsed: dict[str, CCFContract] = {}
    for entry in manifest.artifacts:
        artifact_class = resolve_artifact_class(entry.class_id)
        document = document_paths[entry.key].read_text(encoding="utf-8")
        parsed[entry.key] = load_artifact(document, artifact_class)

    # Phase two: register the ones the manifest marks `role: register`.
    pinned: list[ArtifactPin] = []
    for entry in manifest.artifacts:
        if entry.role == "load":
            # D-IMPL-80. Nothing happens here, deliberately. A `register_typed`
            # call on this branch would content-hash raw event data into Control
            # Plane state and therefore into Decision Replay dimension 2.
            continue
        artifact_class = resolve_artifact_class(entry.class_id)
        if entry.registration == "versioned":
            # `register_versioned` RETURNS its D-05 refusals rather than raising
            # them (the GateRefusal discipline), so a bare assignment here would
            # put a `RefuseUnbumpedChange` object into `ArtifactPin.version` and
            # record a refusal as a pin. The narrowing below is what stops that,
            # and mypy --strict is the second layer.
            #
            # There is deliberately no fallback to `register_typed`: a manifest
            # that declared `versioned` asked for the bump check, and quietly
            # taking the other path when it refuses is the bypass this field
            # exists to close, returning in a new costume.
            #
            # The other failure mode on this branch is a `TypeError` raised
            # inside `register_versioned` when the document declares no string
            # `artifact_version`. It surfaces unhandled, and that is what an
            # adopter sees when they declare `versioned` for a class that is not
            # author-versioned. For the SDK-owned instances of that mistake,
            # `refuse_registration_the_sdk_fixes` refuses in preflight, before
            # any document is read.
            outcome = registry.register_versioned(
                entry.key, parsed[entry.key], artifact_class
            )
            if isinstance(outcome, RegistrationRefusal):
                raise ValueError(
                    f"manifest key {entry.key!r} (class {entry.class_id!r})"
                    " declares registration 'versioned', and the D-05"
                    " hash-verified bump check refused it:"
                    f" {type(outcome).__name__}. Nothing was registered under"
                    " this key, and no pin is recorded for a refusal"
                )
            version = outcome
        else:
            version = registry.register_typed(
                entry.key, parsed[entry.key], artifact_class
            )
        pinned.append(
            ArtifactPin(
                key=entry.key,
                version=version,
                class_id=entry.class_id,
                registration=entry.registration,
            )
        )

    pins = ResolvedPins(entries=tuple(pinned))
    handle = boot(
        database_path=database_path,
        postgres_dsn=postgres_dsn,
        memory=manifest.backend == "memory",
        neo4j_uri=neo4j_uri,
        registry=registry,
        resolution_spec_key=manifest.resolution_spec_key,
        resolution_spec_version=pins.version_for(manifest.resolution_spec_key),
        policy_bundle_key=manifest.policy_bundle_key,
        policy_bundle_version=pins.version_for(manifest.policy_bundle_key),
    )
    return BootedFabric(
        handle=handle,
        pins=pins,
        tenant_id=resolved_tenant,
        artifacts=parsed,
        survivor_cap=manifest.survivor_cap,
    )
