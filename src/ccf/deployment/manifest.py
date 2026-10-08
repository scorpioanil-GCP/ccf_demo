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

The one environment read in ``src/ccf``
--------------------------------------

:func:`_resolve_secret_references` reads the process environment, and it is the
only production environment read under ``src/ccf``. That is a deliberate placement
rather than an accident of where the code was written. :func:`ccf.boot.boot`
takes *values* and reads no environment, which is what keeps the composition
root deterministic and testable; the manifest — the document that names which
references a deployment uses — already lives here, so this is where a name
becomes a value.

What the manifest carries is the *reference*, never the credential (D-08). A
manifest is content-hashed and versioned, so a value written into one would be
persisted into the audit plane forever; a reference name is auditable and holds
nothing secret, and it is what replay pins as "which credential was in force".
See :class:`~ccf.controlplane.artifacts.SecretReference` for the two mechanisms
that make the value's absence structural rather than conventional.

Algorithmic module (CINV-03) — see the package docstring for why file I/O here
is not a contradiction.
"""

from __future__ import annotations

from typing import Any, cast

import dataclasses

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from ccf.authz.capability import (
    CompositionRegister,
    COMPOSITION_PRINCIPAL,
    Authorized,
    Register,
    mint_at_composition,
)
from ccf.assembly.worker import EntityResolutionSpec
from ccf.boot import FabricHandle, boot
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEPLOYMENT_MANIFEST,
    DeploymentManifest,
    ManifestEntry,
    PolicyFilterParametersArtifact,
    load_artifact,
)
from ccf.controlplane.registry import (
    namespaced_key,
    ControlPlaneProtocol,
    CrossTenantKeyRefused,
    RegistrationRefusal,
)
from ccf.deployment.classes import (
    refuse_registration_the_sdk_fixes,
    refuse_role_the_sdk_fixes,
    resolve_artifact_class,
)
from ccf.deployment.keys import DeploymentKeys
from ccf.deployment.pins import ArtifactPin, ResolvedPins
# SEC-023 (`D-IMPL-374`): the refusal now lives beside the view the
# consumer-time check reads; re-exported here under its batch-5 name.
from ccf.graph.protocols import UngovernedClassificationAttribute
from ccf.graph.leases import _without_lock_directory_setting
from ccf.graph.registry import (
    ResolvedBackend,
    ResolvedSecret,
    UnknownBackend,
    declared_names,
    resolve,
    validate_connection,
)

__ccf_mode__ = "algorithmic"

__all__ = ["BootedFabric", "QuestionFabricNotFresh", "UngovernedClassificationAttribute", "load_and_boot", "register_manifest_entries", "manifest_under_tenant", "keys_under_tenant"]


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
            only, each recorded under its manifest key **as placed under the
            deployment's tenant** (`manifest_under_tenant`, `D-IMPL-354`): an
            authored ``policy`` is pinned as ``{tenant}/policy``, and a key
            already under the tenant is unchanged. Look a pin up by that placed
            key — ``booted.pins.version_for(booted.keys.policy_bundle)`` on the
            single-file door, or ``version_for(namespaced_key(tenant=booted.tenant_id,
            key=...))`` with `ccf.controlplane.registry.namespaced_key` — never by
            the bare authored key, which misses with an
            :class:`~ccf.deployment.pins.UnpinnedArtifactError` naming the placed
            key.
        tenant_id: The resolved tenant, from the manifest or from the caller.
        artifacts: Every parsed artifact, **both roles**, keyed by its manifest
            key **as placed under the deployment's tenant** — the same strings
            ``pins`` uses (`D-IMPL-354`). An authored ``product_class`` is read
            back as ``booted.artifacts[booted.keys.product_class]`` or
            ``booted.artifacts[namespaced_key(tenant=booted.tenant_id,
            key="product_class")]``; ``booted.artifacts["product_class"]``
            raises ``KeyError``, and ``.get("product_class")`` returns ``None``.

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
            manifest keys as placed under its tenant (``booted.keys``, or
            `namespaced_key` over the authored ones): explicit deployment
            configuration rather than type introspection.

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
        keys: The manifest keys the single-file derivation chose, by section
            (`D-IMPL-343`; :class:`~ccf.deployment.keys.DeploymentKeys`) —
            what lets a deployment READ ``keys.request_contract`` rather than
            restate ``"request_contract"`` one file over from the document
            that named it. Placed under the tenant like everything else here,
            so each is exactly the string ``artifacts`` is keyed by — and, for a
            ``role: register`` entry, ``pins`` too. ``None`` on the manifest
            form, where every key was
            authored by hand and there is no section vocabulary to derive from;
            the multi-file door is unchanged by this field.
        for_question: Whether this fabric was booted for ONE question, onto a
            substrate the boot verified did not exist before it
            (:class:`QuestionFabricNotFresh` otherwise). SEC-020, ``D-IMPL-378``
            (Dave, 2026-10-07, Q9: *"Enforce a fresh fabric per question
            whenever acquisition exists, including concurrent use"*): a
            governed call refuses to run an acquisition phase over a fabric
            that is not one
            (``src/ccf/products/resolver.py::AcquisitionNeedsAQuestionFabric``),
            and claims the one that is for the one question it may answer.
            ``False`` — the default, and every fabric a deployment boots for
            more than one question — is the positive "this fabric outlives its
            questions"; such a fabric is read, never acquired into.
    """

    handle: FabricHandle
    pins: ResolvedPins
    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    survivor_cap: int | None
    keys: DeploymentKeys | None = None
    for_question: bool = False


class QuestionFabricNotFresh(ValueError):
    """A fabric booted for one question would not be a fresh one.

    SEC-020, ``D-IMPL-378`` (Q9). A question fabric holds nothing another
    question wrote: the boot verifies the substrate does not exist yet, which
    it can do for the development SQLite substrate (a file path that names no
    file, as the paved road mints one per question) and for no other — a
    network store cannot be shown to be fresh by its connection settings, so it
    is refused rather than assumed. Raised before anything is registered or
    booted.
    """


def _refuse_unless_fresh(backend: str, connection: Mapping[str, object] | None) -> None:
    """Raise :class:`QuestionFabricNotFresh` unless ``connection`` names a SQLite file that does not exist yet."""
    from ccf.graph.backends.sqlite_write import ADAPTER_NAME as SQLITE  # noqa: PLC0415 — the one adapter it can verify

    path = (connection or {}).get("database_path")
    if backend != SQLITE or not isinstance(path, (str, Path)):
        raise QuestionFabricNotFresh(
            f"a fabric booted for one question must be a fresh one, and only a"
            f" {SQLITE!r} file that does not exist yet can be verified fresh;"
            f" this boot names the {backend!r} adapter (SEC-020, Q9)"
        )
    if Path(path).exists():
        raise QuestionFabricNotFresh(
            "a fabric booted for one question must be a fresh one, and the"
            " store this boot names already exists — another question may have"
            " written into it (SEC-020, Q9)"
        )


def _resolve_tenant(manifest: DeploymentManifest, supplied: str | None) -> str:
    """Return the one tenant this deployment runs as, or refuse.

    Exactly one source may supply it. Both-absent and a conflicting pair are
    both refused rather than resolved by precedence, mirroring the
    refuse-to-infer posture :func:`ccf.boot.boot` states in its signature — its
    ``backend`` argument is required and has no default — because a deployment
    whose tenant depends on which source won is a deployment whose graph scope
    nobody wrote down (INV-CH7-16, D-IMPL-05).
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


def _preflight_adapter(
    manifest: DeploymentManifest,
    connection: Mapping[str, object],
    *,
    read_only: bool = False,
) -> ResolvedBackend:
    """Refuse an adapter declaration this deployment cannot satisfy (D-08).

    ``read_only`` validates what a read-only boot validates (N-2;
    ``D-IMPL-374``): the connection without the writer-lease setting, because
    a read-only boot takes no writer lease (``ccf.boot.boot``).

    **This runs before any artifact is parsed and before anything is
    registered**, and that ordering is the whole point — it is why this is a
    function here rather than three lines beside the ``boot`` call. A manifest
    naming an adapter the deployment has not installed *parses* perfectly well,
    so a check placed at the end would register every artifact first and fail
    afterwards, leaving Control Plane state from a fabric that never booted.
    That is a replay-integrity problem, not an untidiness: the registry would
    then answer "what was in force" for a deployment that never ran.

    The refusal is loud and there is **no fallback**. A fabric that guessed its
    substrate could boot against a development store in production and still
    pass every test — the posture :func:`ccf.boot.boot` states in its own
    signature, inherited here rather than re-decided.

    **What replaced the table this function used to hold.** It carried a
    mapping from substrate name to required connection argument, edited once
    per adapter forever. Each adapter now declares its own connection contract
    (D-07) and the registry answers which adapters this deployment has. Both of
    that table's refusals survive, by the adapter's contract rather than by a
    branch here: a required setting missing is a required field, and a setting
    the adapter does not take is the ``extra="forbid"`` every adapter contract
    inherits.

    **Message hygiene**, for the refusals built here rather than delegated.
    Each is built from *names* only — the adapter, the field, the variable
    name. The underlying exception's own rendering is never interpolated and
    the supplied value is never read, because Pydantic reproduces a supplied
    value verbatim in a validation error and on this path one of those values
    is a credential (T-15.4-05).

    Raises:
        ccf.graph.registry.UnknownBackend: the manifest names an adapter no
            installed distribution registers.
        ccf.graph.registry.InvalidBackendConfig: ``connection`` does not
            satisfy the declared adapter's own contract — a required setting is
            missing, or a setting the adapter does not take was supplied.
        ValueError: a ``backend_secrets`` entry names a field the declared
            adapter does not declare as a credential field; or discovery found
            a packaging conflict among the installed adapters.
    """
    declared = manifest.backend
    known = declared_names()
    if declared not in known:
        # Built from two names this deployment already holds: the one the
        # manifest declared, and what `declared_names()` returned. This is the
        # payback for deleting the six-name `Literal` — a refusal that can say
        # what IS registered here, which an enumeration in this repository
        # could never do, because it listed what someone had hard-coded rather
        # than what the deployment has.
        available = ", ".join(sorted(known)) if known else "none"
        raise UnknownBackend(
            f"the manifest declares backend {declared!r}, which no installed"
            f" adapter registers. `declared_names()` returns: {available}."
            " Install a distribution that declares that adapter, or correct"
            " the manifest — the fabric does not guess a substrate and does"
            " not fall back."
        )

    record = resolve(declared)
    # The ONE place a connection refusal is built is
    # `ccf.graph.registry.validate_connection`, and this module is the third
    # caller tempted to write its own — after `boot()` and the V11 test. Three
    # hand-written wrappers is how the message contract drifts, and the
    # specific way it drifts is a formatter reaching for the exception's own
    # rendering because it is shorter. That rendering reproduces the value that
    # was supplied, and on this path one of those values is a credential. Do
    # not build a refusal here; call this.
    validate_connection(
        record.registration,
        _without_lock_directory_setting(record.registration.config_model, connection)
        if read_only
        else connection,
    )
    _refuse_undeclared_secret_fields(manifest, record)
    return record


def _refuse_undeclared_secret_fields(
    manifest: DeploymentManifest, record: ResolvedBackend
) -> None:
    """Refuse a credential reference the declared adapter has no field for.

    ``secret_fields`` on the adapter's registration record is the whole
    vocabulary of credentials that adapter accepts, so "a credential declared
    for an adapter that takes none" is answerable from the record alone — no
    list lives here, and nothing here changes when a seventh adapter arrives.

    Refused in preflight, on :func:`_preflight_adapter`'s ordering argument,
    and therefore **before the named variable is read**: a reference the
    adapter cannot use is a manifest error, and reading the environment to
    discover that would pull a live credential into this process for nothing.

    The message is built from names only — the adapter, the offending field,
    and the fields the adapter does declare. No value of any kind appears in
    it, and no environment variable is consulted to build it.
    """
    accepted = record.registration.secret_fields
    for reference in manifest.backend_secrets:
        if reference.field in accepted:
            continue
        declares = ", ".join(sorted(accepted)) if accepted else "none"
        raise ValueError(
            f"the manifest declares backend {record.registration.name!r} and a"
            f" `backend_secrets` entry for the field {reference.field!r},"
            " which that adapter does not declare as a credential field. It"
            f" declares: {declares}. Remove the entry, or name a field the"
            " adapter takes."
        )


def _resolve_secret_references(
    manifest: DeploymentManifest, record: ResolvedBackend
) -> dict[str, ResolvedSecret]:
    """Read each declared credential reference, keyed by adapter config field.

    **The one production environment read in** ``src/ccf``, and it belongs in
    this wiring layer rather than in :mod:`ccf.boot`. ``boot()`` takes values
    and reads no environment, which is what keeps the composition root
    deterministic and testable; the manifest — the document that names the
    references — already lives here.

    Each entry becomes one :class:`~ccf.graph.registry.ResolvedSecret`, which
    carries the field, the *name* of the variable it was read from, and the
    value wrapped in ``pydantic.SecretStr``. The reference name has to travel
    **with** the value: this function is the only place in the system that
    knows a given config field was satisfied from a given variable, and
    :attr:`ccf.graph.registry.AdapterPin.secret_refs` is where that fact is
    pinned. A plain mapping of field to value would leave the pin able to
    record only the field name — which says a credential was used and not
    *which one*, weaker than D-08 and D-09 require.

    **Unset and empty are both refusals, never fallbacks.** A manifest that
    names a reference has asserted a credential is required, and the fabric
    does not fall back to an anonymous connection. That is the direct lesson of
    WR-02/WR-03, where a credentialed URL connected anonymously because the
    wire client derives no authorization header from ``base_url`` userinfo: the
    failure was silent, and a refusal here is what stops it arriving through a
    new door.

    Raises:
        ValueError: a named variable is unset, or is set to the empty string.
            The message names the adapter, the field and the variable **name**,
            and never the value — there is no value to name in the unset case,
            and naming it in the empty case would be the disclosure this whole
            path is arranged to prevent.
    """
    resolved: dict[str, ResolvedSecret] = {}
    for reference in manifest.backend_secrets:
        # The process environment is read on the next line and nowhere else
        # under `src/ccf`. The value is bound only to reach `SecretStr`; the
        # refusal below is built from the three names above it, never from
        # `value`.
        value = os.environ.get(reference.env_var)
        if not value:
            raise ValueError(
                f"the manifest declares backend {record.registration.name!r}"
                f" with a credential for the field {reference.field!r} from"
                f" the environment variable {reference.env_var!r}, which is"
                " unset or empty. A manifest that names a reference has"
                " asserted a credential is required, so the fabric refuses"
                " rather than connecting anonymously — set the variable, or"
                " remove the `backend_secrets` entry."
            )
        resolved[reference.field] = ResolvedSecret(
            field=reference.field,
            ref_name=reference.env_var,
            value=SecretStr(value),
        )
    return resolved


def _preflight_entries(manifest: DeploymentManifest, root: Path) -> dict[str, Path]:
    """Refuse every entry the SDK already knows is wrong, before anything is read.

    Runs :func:`~ccf.deployment.classes.refuse_role_the_sdk_fixes`,
    :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes` and
    :func:`_document_inside_the_deployment` over every entry, in that order,
    and returns the key → resolved-path mapping the manifest form's own parse
    phase reads from next.

    **Shared by both entry points** (`16-30`) — :func:`load_and_boot` and
    :func:`~ccf.deployment.config.load_config_and_boot` — so the preflight
    cannot drift between them the way a second copy of the register loop
    could (see :func:`_register_and_boot`'s own docstring for that argument,
    which is the same argument one level earlier).

    The config form calls this too, even though its documents are already in
    memory and it never reads the returned mapping back: running the
    preflight is what holds a *derived* manifest to the same refusal surface
    an *authored* one gets. A check skipped for the new door is a door the
    audit plane knows less about.
    """
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
    return document_paths


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _tenant_of_key(key: str) -> str:
    """The tenant segment of a manifest key, derived exactly as the registry derives it.

    The Control Plane key grammar is ``{tenant}/{class}/{name}`` and the
    registry's one tenant comparison (``D-IMPL-353`` §1.3) reads the text
    before the first ``/``. This module derives the same segment to mint for
    — it invents no tenant — and a key with no segment is refused here with
    the registry's own error, before anything is minted, because a key that
    names no tenant belongs to nobody.
    """
    tenant, separator, _ = key.partition("/")
    if not separator or not tenant:
        raise CrossTenantKeyRefused(
            f"manifest key {key!r} has no tenant segment; a Control Plane key is"
            " `{tenant}/{class}/{name}`, and a composition root mints Register"
            " for the key's own tenant and no other (D-IMPL-353 §1.3;"
            " D-IMPL-354)"
        )
    return tenant


def _mint_register(registry: ControlPlaneProtocol, key: str, *, tenant: str) -> Authorized[CompositionRegister]:
    """The composition recipe for ONE manifest entry (D-IMPL-354).

    This module is a composition root: the deployment's own registrations at
    boot are the deployment acting on its own fabric, and no served caller
    requests them, so no door can mint for them. The decision is recorded on
    the Control Plane's own audit log as a ``composition`` event and the
    capability carries that event's content address as its ``decision_id``.
    One key per capability; the registry then takes the key FROM the
    capability and compares its tenant segment once.
    """
    segment = _tenant_of_key(key)
    if segment != tenant:
        # The composition root says which tenant it composes for; the key's own
        # segment is checked AGAINST that, never read as it. A key under another
        # tenant is refused before anything is appended or minted — the loader
        # placed every key it derived under the resolved tenant, so this fires
        # only for a caller that skipped that placement (D-IMPL-354; the
        # D-IMPL-353 join's panel).
        raise CrossTenantKeyRefused(
            f"manifest key {key!r} is under tenant {segment!r} and this"
            f" composition mints for {tenant!r}; a composition root places its"
            " keys under its own tenant (`manifest_under_tenant`) before the"
            " register loop, and the loop mints for no other (D-IMPL-354)"
        )
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
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def _refuse_ungoverned_classification(
    manifest: DeploymentManifest, parsed: Mapping[str, CCFContract]
) -> None:
    """Refuse a deployment whose access-deciding attribute is source-asserted (SEC-023).

    Reads the resolution spec at ``manifest.resolution_spec_key`` and every
    parsed :class:`~ccf.controlplane.artifacts.PolicyFilterParametersArtifact`.
    Static only: two declarations compared before anything is materialized,
    on the R-10 precedent (``src/ccf/deployment/config.py::_refuse_unproducible_seed_classes``).
    A spec key that does not resolve to an
    :class:`~ccf.assembly.worker.EntityResolutionSpec` is left to
    :func:`ccf.boot.boot`, which refuses it by type.

    The EARLY refusal (``D-IMPL-374`` ruling (3) (a)): the same rule is
    enforced again wherever a classification consumer is built or used —
    ``build_operator_registry``, ``PolicyFilter.apply`` and the booted
    fabric's reader — which is what covers the paths that never pass through
    this function.
    """
    spec = parsed.get(manifest.resolution_spec_key)
    if not isinstance(spec, EntityResolutionSpec):
        return
    governed = spec.governed_attributes()
    written = {
        (rule.entity_class, attribute)
        for rule in spec.entity_rules
        for attribute in rule.attribute_keys
    }
    for key, artifact in sorted(parsed.items()):
        if not isinstance(artifact, PolicyFilterParametersArtifact):
            continue
        for entity_class, attribute in sorted(
            artifact.classification_attribute_by_class.items()
        ):
            if (entity_class, attribute) not in written:
                continue
            if attribute not in governed.get(entity_class, {}):
                raise UngovernedClassificationAttribute(
                    operator_key=key, entity_class=entity_class, attribute=attribute
                )


def _register_and_boot(
    manifest: DeploymentManifest,
    parsed: Mapping[str, CCFContract],
    *,
    registry: ControlPlaneProtocol,
    connection: Mapping[str, object] | None,
    secrets: Mapping[str, ResolvedSecret],
    resolved_tenant: str,
    keys: DeploymentKeys | None = None,
    read_only: bool = False,
    for_question: bool = False,
) -> BootedFabric:
    """Register the ``role: register`` entries and boot — the spine both doors share.

    ``read_only`` is handed to :func:`ccf.boot.boot` unchanged (FW-2;
    ``D-IMPL-374``): the registration loop runs either way, into the caller's
    registry, because the pins a read-only fabric reads under are the same
    pins.

    Phase two of the three-phase ordering :func:`load_and_boot`'s own
    docstring states, extracted rather than duplicated (`16-30`). Three
    things here are easy to get subtly wrong and expensive to get wrong
    twice: the D-05 bump-check dispatch's own narrowing (below) that stops a
    returned :class:`~ccf.controlplane.registry.RegistrationRefusal` being
    recorded as a pin, the deliberate absence of a fallback to
    ``register_typed``, and the :class:`ArtifactPin` construction that **is**
    replay dimension 2. A second copy would drift, and the drift would be
    invisible until a replay disagreed — which is why
    :func:`~ccf.deployment.config.load_config_and_boot`
    calls this function rather than carrying its own loop.

    ``parsed`` carries every entry — both roles — already validated against
    its declared class; this function is what decides which of them enter
    the Control Plane.
    """
    # D-IMPL-354 (join): every key the deployment derived or authored lives under
    # the tenant it resolved — a bare `product_class` becomes
    # `{tenant}/product_class` here, once, before anything is minted,
    # registered or composed; a key an author placed under another tenant is
    # refused here, before minting. The registry's tenant-segment check
    # (§1.3) then holds for the manifest root as a real check.
    # SEC-020 (Q9, `D-IMPL-378`): a fabric booted for one question is verified
    # fresh before anything is registered or booted.
    if for_question:
        _refuse_unless_fresh(manifest.backend, connection)
    manifest, parsed, keys = manifest_under_tenant(manifest, parsed, keys, tenant=resolved_tenant)
    # SEC-023 (`D-IMPL-372`): before anything is registered or minted, a
    # deployment whose Policy operator admits on a source-asserted attribute
    # with no declared authority refuses to boot, by name.
    _refuse_ungoverned_classification(manifest, parsed)
    # Phase two: register the ones the manifest marks `role: register`.
    pinned = register_manifest_entries(manifest, parsed, registry=registry, tenant=resolved_tenant)
    pins = ResolvedPins(entries=pinned)
    handle = boot(
        backend=manifest.backend,
        connection=connection or {},
        secrets=secrets,
        registry=registry,
        resolution_spec_key=manifest.resolution_spec_key,
        resolution_spec_version=pins.version_for(manifest.resolution_spec_key),
        policy_bundle_key=manifest.policy_bundle_key,
        policy_bundle_version=pins.version_for(manifest.policy_bundle_key),
        # D-IMPL-354: the one tenant this deployment runs as is the one tenant
        # the fabric is composed for; `boot` mints its invalidation-register
        # capability from this and nothing else.
        tenant_ids=(resolved_tenant,),
        read_only=read_only,
    )
    return BootedFabric(
        handle=handle,
        pins=pins,
        tenant_id=resolved_tenant,
        artifacts=parsed,
        survivor_cap=manifest.survivor_cap,
        keys=keys,
        for_question=for_question,
    )


def keys_under_tenant(keys: DeploymentKeys, *, tenant: str) -> DeploymentKeys:
    """The resolver's :class:`~ccf.deployment.keys.DeploymentKeys`, every key placed under ``tenant``.

    Every ``str`` field and every member of every ``tuple`` field goes through
    :func:`~ccf.controlplane.registry.namespaced_key`; a ``None`` stays ``None``.
    Idempotent — a key already under ``{tenant}/`` comes back unchanged — so the
    keys a deployment authored in the full grammar are exactly the keys it
    resolves by, and a bare section name resolves by the string the loader
    registered it under (D-IMPL-354). :func:`open_product` computes these once
    and exposes them as :attr:`OpenedProduct.keys`; the loader applies them
    through :func:`manifest_under_tenant`.
    """
    moved: dict[str, object] = {}
    for field in dataclasses.fields(keys):
        value = getattr(keys, field.name)
        if isinstance(value, str):
            moved[field.name] = namespaced_key(tenant=tenant, key=value)
        elif isinstance(value, tuple):
            moved[field.name] = tuple(namespaced_key(tenant=tenant, key=item) for item in value)
    return dataclasses.replace(keys, **cast(dict[str, Any], moved))


def manifest_under_tenant(
    manifest: DeploymentManifest,
    parsed: Mapping[str, CCFContract],
    keys: DeploymentKeys | None,
    *,
    tenant: str,
) -> tuple[DeploymentManifest, Mapping[str, CCFContract], DeploymentKeys | None]:
    """Place every Control Plane key the deployment names under ``tenant``.

    The derivation a composition root applies to a derived manifest BEFORE
    handing it to :func:`register_manifest_entries` — the loader here and the
    consumer chain :func:`ccf.products.product.open_product` derives both call
    it; a direct caller of the register loop calls it too, because the loop
    itself admits only keys already under a tenant (D-IMPL-354).

    One derivation, :func:`~ccf.controlplane.registry.namespaced_key`, applied
    to the manifest's entries and its two boot keys, to the parsed-artifact
    mapping keyed by those entries, and to the resolver's
    :class:`~ccf.deployment.keys.DeploymentKeys` — so the key an artifact is
    registered under and the key the resolver later resolves are the same
    string by construction (D-IMPL-354; D-IMPL-353 §1.3).
    """

    def under(key: str) -> str:
        return namespaced_key(tenant=tenant, key=key)

    entries = tuple(entry.model_copy(update={"key": under(entry.key)}) for entry in manifest.artifacts)
    renamed = manifest.model_copy(
        update={
            "artifacts": entries,
            "resolution_spec_key": under(manifest.resolution_spec_key),
            "policy_bundle_key": under(manifest.policy_bundle_key),
        }
    )
    rekeyed = {under(key): artifact for key, artifact in parsed.items()}
    return renamed, rekeyed, None if keys is None else keys_under_tenant(keys, tenant=tenant)


def register_manifest_entries(
    manifest: DeploymentManifest,
    parsed: Mapping[str, CCFContract],
    *,
    registry: ControlPlaneProtocol,
    tenant: str,
    only: frozenset[str] | None = None,
) -> tuple[ArtifactPin, ...]:
    """Register the ``role: register`` entries through the path each declares — ONE loop.

    ``tenant`` is the tenant this composition root composes for: every entry's
    key must be under it (the loader's ``manifest_under_tenant`` puts it there),
    and the loop mints ``Register`` for that tenant and no other. A key under
    another tenant is refused by name before anything is minted or registered
    (D-IMPL-354; the D-IMPL-353 join's panel finding that a tenant read off the
    key and then checked against the key was no check).

    Phase two of :func:`load_and_boot`'s ordering, as a function of its own so
    that the one other caller with a reason to register manifest entries
    without booting — :func:`ccf.products.product.open_product`, which must
    have the composing agent, its skills and the policy regime on the Control
    Plane before the grant ledger can resolve them, and which boots nothing
    at open — runs this loop rather than a copy of it. The D-05 dispatch, the
    deliberate absence of a fallback to ``register_typed`` and the
    :class:`ArtifactPin` construction that IS replay dimension 2 all live
    here once.

    Args:
        manifest: The manifest whose entries are registered.
        parsed: Every entry's document, validated against its class.
        registry: The Control Plane registered into.
        only: The keys to register, or ``None`` for every ``register`` entry.
            An entry outside the set is skipped, never refused: the caller
            names a subset of what a full boot registers, and the full boot
            registers the same content again, idempotently.

    Returns:
        One pin per registered entry, in manifest order.
    """
    pinned: list[ArtifactPin] = []
    for entry in manifest.artifacts:
        if only is not None and entry.key not in only:
            continue
        if entry.role == "load":
            # D-IMPL-80. Nothing happens here, deliberately. A `register_typed`
            # call on this branch would content-hash raw event data into Control
            # Plane state and therefore into Decision Replay dimension 2.
            continue
        artifact_class = resolve_artifact_class(entry.class_id)
        # D-IMPL-354: one `Register` capability per entry, for exactly this
        # key, minted by the recipe above. The registry takes the key from the
        # capability; nothing below passes a key.
        authorized = _mint_register(registry, entry.key, tenant=tenant)
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
                authorized, parsed[entry.key], artifact_class
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
                authorized, parsed[entry.key], artifact_class
            )
        pinned.append(
            ArtifactPin(
                key=entry.key,
                version=version,
                class_id=entry.class_id,
                registration=entry.registration,
            )
        )

    return tuple(pinned)


def load_and_boot(
    manifest_path: str | Path,
    *,
    registry: ControlPlaneProtocol,
    connection: Mapping[str, object] | None = None,
    tenant_id: str | None = None,
    read_only: bool = False,
    for_question: bool = False,
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
       lies inside the deployment**, and the declared adapter against what this
       deployment has installed and against ``connection`` — all before any
       document is read and before anything is registered.
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
    ``booted.artifacts[<signal-batch-key>].envelopes`` — every key here as
    placed under the tenant, see :attr:`BootedFabric.artifacts` — through
    ``booted.handle.worker``, builds a view from ``booted.handle.reader``,
    assembles the ``parameters`` mapping for the operator-registry builder by
    naming its own manifest keys against ``booted.artifacts``, and mints the
    MAX_TTL registration and the product-class registration itself. That last
    part is deliberate: the TTL pin must stay an independently authored
    registration, or Gate 3 compares a ceiling against itself.

    **No temporal write guard runs on that road.** The paved road composes
    :class:`~ccf.signal.envelope.IngressTemporalBound` at its acquisition seam and
    judges every envelope before L2's writer; an adopter ingesting through
    ``booted.handle.worker`` composes its own with
    :meth:`~ccf.signal.envelope.IngressTemporalBound.at_composition` and calls
    :meth:`~ccf.signal.envelope.IngressTemporalBound.refuse_outside_window` before
    each ``ingest``. Nothing in the SDK does it for a low-road ingest loop, and
    nothing refuses the loop that omits it (ruled outside SEC-008 B1 — Dave,
    2026-10-04, `D-IMPL-364`).

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
        connection: The declared adapter's connection settings, keyed by the
            field names on that adapter's own connection contract and validated
            against it. One mapping, not a keyword per substrate: the keys and
            their meaning belong to the adapter, so this function has nothing
            to enumerate and nothing to edit when a seventh adapter arrives.

            **Caller-supplied, deliberately, and this is the line the manifest
            does not cross.** A connection string is environment material —
            a DSN or a URI can carry credentials — and a manifest is
            content-hashed and versioned, so putting one there would persist it
            into the audit plane forever. What the manifest *does* carry is the
            reference to a credential (``backend_secrets``), which is auditable
            and holds nothing secret.
        tenant_id: The deployment's tenant, when the manifest does not name it.
        read_only: ``True`` boots the fabric read-only through
            ``ccf.boot.boot(..., read_only=True)`` (FW-2, whole-branch review
            I-1; ``D-IMPL-374``): a governed reader, no writer and no writer
            lease — the fabric Decision Replay reads through beside a live
            writer. The preflight and the boot both set the connection's
            writer-lease setting aside, so it is neither validated nor used
            (N-2). ``False`` (the default) is the writer boot, unchanged.
        for_question: ``True`` boots the fabric for ONE question (SEC-020,
            ``D-IMPL-378`` Q9): the substrate is verified fresh first
            (:class:`QuestionFabricNotFresh` otherwise) and the returned
            :class:`BootedFabric` says so, which is what lets a governed call
            run an acquisition phase over it — once. ``False`` (the default)
            boots a fabric that may answer many questions and is never
            acquired into.

    Raises:
        ccf.graph.registry.UnknownBackend: the manifest names an adapter no
            installed distribution registers. The refusal lists what
            :func:`ccf.graph.registry.declared_names` returns, which is the
            payback for the six-name ``Literal`` this replaced.
        ccf.graph.registry.InvalidBackendConfig: ``connection`` does not satisfy
            the declared adapter's contract — a required setting is missing, or
            a setting the adapter does not take was supplied. Built by
            :func:`ccf.graph.registry.validate_connection` and nowhere else, so
            it cannot reproduce a value that was supplied.
        ValueError: the tenant is absent from both sources or conflicts between
            them; a ``backend_secrets`` entry names a field the declared adapter
            does not declare as a credential field; a ``backend_secrets``
            entry's environment variable is unset or empty — a named reference
            that does not resolve is a refusal, never a fall-back to an
            anonymous connection; an entry's ``path`` resolves outside the
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
    document_paths = _preflight_entries(manifest, root)
    adapter = _preflight_adapter(manifest, connection or {}, read_only=read_only)
    # After the preflight, deliberately: a reference the adapter cannot use is
    # refused above, without the environment ever being read, so the only
    # variables read here are ones the declared adapter actually accepts. Still
    # before any document is parsed and before anything is registered, so a
    # mis-set variable leaves the Control Plane exactly as this call found it.
    secrets = _resolve_secret_references(manifest, adapter)

    # Phase one: parse everything. Nothing is registered until every document in
    # the manifest has been read and validated.
    parsed: dict[str, CCFContract] = {}
    for entry in manifest.artifacts:
        artifact_class = resolve_artifact_class(entry.class_id)
        document = document_paths[entry.key].read_text(encoding="utf-8")
        parsed[entry.key] = load_artifact(document, artifact_class)

    return _register_and_boot(
        manifest,
        parsed,
        registry=registry,
        connection=connection,
        secrets=secrets,
        resolved_tenant=resolved_tenant,
        read_only=read_only,
        for_question=for_question,
    )
