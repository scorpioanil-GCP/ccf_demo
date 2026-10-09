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

from typing import Annotated, Any, Literal, Union, cast, get_args, get_origin

import dataclasses

import os
import stat
import types
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath

from pydantic import SecretStr

try:  # pragma: no cover - import shape only
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - a platform without flock
    _fcntl = None  # type: ignore[assignment]

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
from ccf.controlplane.demonstration_serve_instant import (
    DEMONSTRATION_SERVE_INSTANT,
    refuse_misplaced_demonstration_serve_instants,
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
from ccf.graph.protocols import GraphReader, UngovernedClassificationAttribute
from ccf.graph.leases import _LOCK_DIRECTORY_SETTING, _without_lock_directory_setting
from ccf.graph.registry import (
    ResolvedBackend,
    ResolvedSecret,
    UnknownBackend,
    declared_names,
    resolve,
    validate_connection,
)

__ccf_mode__ = "algorithmic"

__all__ = ["BootedFabric", "DeploymentStoreNotEmpty", "DeploymentStoreNotVerified", "ManifestKeysPlaceToOneKey", "QuestionFabricNotExclusive", "QuestionFabricNotFresh", "QuestionStoreNotEmpty", "UngovernedClassificationAttribute", "load_and_boot", "register_manifest_entries", "manifest_under_tenant", "keys_under_tenant"]


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
            is still absent from ``pins``, and the boot registers it nowhere and
            pins it nowhere. ``artifacts`` is a parse result handed back to the
            caller; ``pins`` is the record of what was put in force. One
            mechanism other than the boot does register and pin from a
            ``role: load`` entry: a governed resolver built over this fabric
            registers, when it is built (`D-IMPL-378` R-A), the TYPED request
            contract it derives from the deployment's request-contract entry,
            whatever that entry's role, under the same key at the typed
            contract's own content address, and every decision that resolved a
            request against it pins it there on replay dimension 2
            (`D-IMPL-310`; ``src/ccf/products/resolver.py::GovernedResolver``).
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
            (:class:`QuestionFabricNotFresh` otherwise) and that held nothing
            for its tenant when the boot returned (:class:`QuestionStoreNotEmpty`
            otherwise; SEC-020 P4s-A (b)). SEC-020, ``D-IMPL-378``
            (Dave, 2026-10-07, Q9: *"Enforce a fresh fabric per question
            whenever acquisition exists, including concurrent use"*): a
            governed call refuses to run an acquisition phase over a fabric
            that is not one
            (``src/ccf/products/resolver.py::AcquisitionNeedsAQuestionFabric``),
            and claims the one that is for the one question it may answer.
            ``False`` — the default, and every fabric a deployment boots for
            more than one question — is the positive "this fabric outlives its
            questions"; such a fabric is read, never acquired into.
        question_store: Whether the store this fabric reads was booted for one
            question — by this boot (``for_question=True``) or by an earlier
            one, which left a durable marker beside every path naming the
            store (``<resolved path>.ccf-question-store``). SEC-020 P4 (a),
            ``D-IMPL-378`` (ruled by Dave, 2026-10-08 12:29 MST): a governed call
            over a question's store booted again — ``question_store`` without
            ``for_question`` — is refused before anything is read
            (``src/ccf/products/resolver.py::QuestionStoreReopened``), while
            Decision Replay, which rebuilds a resolver over the store without
            calling it, reads it as before. Read from the marker, never from
            the store's contents. A store whose settings name no path carries
            no marker, and cannot be booted for a question.
        store_creation: Whether the SDK can vouch for how the store this
            fabric reads was created. SEC-020 P4 (a) made strict,
            ``D-IMPL-378`` (Dave, 2026-10-08 12:29 MST: *"An unmarked existing
            store must not be presumed fresh. Require verifiable fresh creation
            or refuse acquisition-backed serving. Unsupported network
            compositions must refuse before questions run."*). Every store a
            boot through this module creates at a path gets a marker beside it,
            created exclusively before the store exists: the question marker
            on a boot for one question, ``<resolved path>.ccf-deployment-store``
            on any other boot. ``"verified"``: every path naming the store
            carries a question marker, or a deployment marker that records a
            completed verification, written by this boot or an earlier one. A
            deployment marker reads ``pending`` from its creation until the
            boot that created it has read the store once and found nothing for
            the tenant (:class:`DeploymentStoreNotEmpty` otherwise, which
            removes it; OWED-RULINGS-3 item 2A (b), ``D-IMPL-378``), and
            ``verified`` only after; a boot meeting a deployment marker that
            reads anything else, or one that reads ``verified`` with no store
            beside it, is refused (:class:`DeploymentStoreNotVerified`;
            repairs 1.1 and 1.2, ``D-IMPL-378``). A plain boot holds the
            store-creation lock of every path from its look at the path to the
            hand-back, so a boot that finds another creating the store waits
            for it. Read when the boot hands the fabric back, after its read,
            never before it.
            ``"unmarked"``: the store existed at boot and carries neither — a
            store booted for a question before the markers existed, a copy
            taken without its marker, a store created outside these doors —
            so nothing shows that no question's acquisition wrote into it, and
            a governed call over it is refused before the graph is read
            (``src/ccf/products/resolver.py::UnmarkedStoreNotPresumedFresh``).
            ``"unverifiable"``: the adapter's connection names no path, so no
            boot can show the store fresh and none can mark it; an acquisition
            composition over it is refused when its resolver is constructed,
            and the paved road over such a substrate when it is opened
            (``src/ccf/products/resolver.py::AcquisitionOverUnverifiableStore``).
            The default, for a value this module did not produce, is
            ``"unmarked"``: nothing is presumed. Read from the markers, never
            from the store's contents; a marker binds to its store by path
            alone, so it vouches for reuse by deployments and operators, not
            against an actor who can write into the store's directory.
    """

    handle: FabricHandle
    pins: ResolvedPins
    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    survivor_cap: int | None
    keys: DeploymentKeys | None = None
    for_question: bool = False
    question_store: bool = False
    store_creation: Literal["verified", "unmarked", "unverifiable"] = "unmarked"


class QuestionFabricNotFresh(ValueError):
    """A fabric booted for one question would not be a fresh one.

    SEC-020, ``D-IMPL-378`` (Q9). A question fabric holds nothing another
    question wrote: the boot verifies it from the adapter's own validated
    connection settings — every path-valued setting must name a path that does
    not exist yet, and there must be one. A file-backed development substrate,
    minted at a new path per question as the paved road mints it, passes; a
    substrate whose settings name no path (a network store's address and
    credentials) cannot be shown fresh by them and is refused rather than
    assumed. Raised before anything is registered.

    **And the path is reserved for this boot alone** (SEC-020 P4 (a) made
    strict; Dave, 2026-10-08 12:29 MST: *"Require verifiable fresh
    creation"*): after registration and before the store is booted, each
    path's question marker is created exclusively, so a second boot for a
    question at a path another boot holds is raised here, and so is a store,
    or another boot's deployment marker, that appeared at a path after the
    check. The SDK then creates nothing at the store's path itself — the
    adapter does, at the boot — so a store another actor writes at the path
    after this last check is opened as the one this boot created; when the
    boot returns, the store is read once and refused if it holds anything
    for the tenant (:class:`QuestionStoreNotEmpty`). A boot for a question
    that would hold no writer lease is refused before anything is registered
    (:class:`QuestionFabricNotExclusive`).
    """


class QuestionStoreNotEmpty(QuestionFabricNotFresh):
    """A fabric booted for one question opened a store that already holds claims for its tenant.

    SEC-020 P4s-A (b), ``D-IMPL-378`` (Dave, 2026-10-08 16:40 MST: *"Add the
    emptiness check and keep unverifiable stores free of acquisition. The
    check must precede acquisition and remain protected by exclusive
    ownership through use."*). The boot reserves a question's path and checks
    it again before the adapter opens it, and the adapter creates the store
    at the boot, so a store written at the path between that last check and
    the open was booted as the question's fabric (measured: a used question
    store copied there, and the deployment's own plain boot filling one
    there). Now, after the adapter opens the store and the boot takes its
    writer lease, and before the fabric is handed back, the store is read
    once through the governed reader, at the latest instant a timestamp can
    name; a store holding any entity or relationship for the
    fabric's tenant is closed and refused here, before any acquisition phase
    or governed call, so the refusal reads nothing about a question's subject
    and is the same for every subject. The question marker stays beside the
    store, so a later boot of that path keeps refusing it.

    What the one read does not see is stated in the security how-to, section
    4.12: a claim superseded before that instant with no current successor
    (no SDK writer leaves one; a store written outside the SDK can hold one),
    a store holding rows only for another tenant, and a write into the store,
    after the read, by a writer outside the SDK's writer lease.
    """


class QuestionFabricNotExclusive(QuestionFabricNotFresh):
    """A boot for one question that would hold no writer lease, refused before anything is registered.

    SEC-020 P4s-A (b), ``D-IMPL-378`` (Dave, 2026-10-08 16:40 MST: *"The
    check must precede acquisition and remain protected by exclusive
    ownership through use."*). From its emptiness check
    (:class:`QuestionStoreNotEmpty`) to the question's end, a question's store
    is held by the question marker its boot created exclusively, which
    refuses a second boot for a question at the path, and by the writer lease
    its boot holds until the handle is closed, which refuses another writer
    boot of the path (``src/ccf/graph/_writer.py::SingleWriterViolation``);
    a plain boot that only reads the store is refused at its governed call
    (``src/ccf/products/resolver.py::QuestionStoreReopened``). A read-only
    boot (``read_only=True``) takes no writer lease: booted for a question,
    another writer boot of the same path wrote into its store while its
    fabric was open, and the fabric read what it wrote (measured). So a boot
    for a question that is also read-only is refused by name, before anything
    is registered or created at its path. Decision Replay reads a question's
    store through a read-only boot that is not for a question, which is
    unaffected.
    """


class DeploymentStoreNotEmpty(ValueError):
    """A plain boot that created its store opened a store that already holds claims for its tenant.

    SEC-020, ``D-IMPL-378`` OWED-RULINGS-3 item 2A (b) (Dave, 2026-10-09 06:21
    MST: *"2A(b)"*). The option he ruled, on the sheet he ruled from: *"Run
    the same one emptiness read when a plain boot creates a new store (one
    read per store creation, no Protocol change; reopening is unaffected)."*
    The build first took a lane's narrower wording (*"A plain boot that created
    its deployment marker in this boot"*); repair 1.2 (Dave, 2026-10-09 10:54
    MST: *"Run the emptiness check whenever a plain boot creates a new
    store."*) restores the ruled trigger: the read is taken by every plain boot
    whose path held no store when it looked, whoever made a marker beside it
    (a store created where a question marker stands included), while the boot
    holds the store-creation lock. A boot not for a question leaves its
    deployment marker beside a path that holds no store and no marker, and the
    adapter creates the store at the boot, so a store written at the path after
    the marker and before the adapter opened it was booted as the deployment's
    own, with the marker vouching for it (measured: a used question store
    written there was booted with ``store_creation`` ``"verified"``, and a later
    governed call over it was answered). Now the boot that created the marker
    reads the store once, through the governed reader at the latest instant a
    timestamp can name, after the adapter opens it and before the fabric is
    handed back — the read a boot for a question takes
    (:class:`QuestionStoreNotEmpty`) — and a store holding any entity or
    relationship for the tenant is closed and refused here. The markers this
    boot created are removed first, as a refused question reservation removes
    its own, so the path is left holding a store with no marker beside it, over
    which no governed call is answered
    (``src/ccf/products/resolver.py::UnmarkedStoreNotPresumedFresh``). A boot
    that reopens a store (the path held a store, or a marker, before the boot)
    takes no read.

    The read sees what a question boot's read sees and has the same limits
    (the security how-to, section 4.12). A boot whose path carries a
    deployment marker with no store beside it creates nothing: it is refused
    first (:class:`DeploymentStoreNotVerified`, reason ``"no-store"``). The
    refusal states no count and nothing the store holds.
    """


#: Why :class:`DeploymentStoreNotVerified` refused, by its ``reason``: what the marker (or its lock) shows.
_NOT_VERIFIED_WHY = {
    "pending": (
        "records a store creation whose emptiness read never completed (state pending: the boot that"
        " created it was killed or interrupted before it finished, or something outside the SDK wrote it)"
    ),
    "unreadable": (
        "records no state in the form this SDK writes (a marker written before markers recorded their"
        " state, text the SDK did not write, or not a regular file this process can read)"
    ),
    "no-store": (
        "records a verified store creation, but no store stands beside it: that store was deleted or"
        " moved, and a marker that never saw the store a boot would create there now cannot vouch for it"
    ),
    "claimed": (
        "appeared at the path after the boot looked, or was replaced or rewritten while the boot that"
        " created it was verifying its store, so something outside the SDK's boots writes beside the store"
    ),
    "lock-unavailable": "cannot be checked, because the store-creation lock beside it cannot be taken",
}

#: What an operator does about each :class:`DeploymentStoreNotVerified` ``reason``: the end of its text.
_NOT_VERIFIED_REMEDY = {
    "pending": (
        "inspect the marker and the store beside it, then remove the marker (and the store, if one"
        " stands there) so that a boot creates and verifies a new store"
    ),
    "unreadable": (
        "inspect the marker and the store beside it, then remove the marker (and the store, if one"
        " stands there) so that a boot creates and verifies a new store"
    ),
    "no-store": (
        "find where the marker's store went, then remove the marker so that a boot creates and verifies"
        " a new store"
    ),
    "claimed": (
        "find what writes into the store's directory, then remove the marker (and the store, if one"
        " stands there) so that a boot creates and verifies a new store"
    ),
    "lock-unavailable": (
        "make the lock's path a regular file this process can open and lock with flock, on a filesystem"
        " whose flock works"
    ),
}


class DeploymentStoreNotVerified(ValueError):
    """A plain boot where safe verification cannot be established: refused, and left for an operator to resolve.

    SEC-020, ``D-IMPL-378`` repair 1.1 (Dave, 2026-10-09 10:54 MST, verbatim:
    *"Remove markers created by this boot on every failed-boot path, including
    failure during close. Remove only markers this boot owns. A marker left by
    a crash must not imply completed verification."*) and repair 1.2 (*"Run the
    emptiness check whenever a plain boot creates a new store. Serialize
    creation and verification; test competing boots. If safe verification
    cannot be established, refuse until an operator resolves the stale
    marker."*). A plain boot holds the store-creation lock of every path naming
    its store (``<resolved path>.ccf-store-creation.lock``) from its look at the
    path through the hand-back, so a boot that finds another creating the store
    waits for it to finish. A boot that creates its
    store at a path leaves its deployment marker there first, reading
    ``pending`` and carrying a token of its own, and makes it read ``verified``
    only once its emptiness read has completed (:class:`DeploymentStoreNotEmpty`
    otherwise), atomically and durably. Every failed boot removes the markers it
    created that are still its own — the same file, carrying its token —
    whatever failed: ``boot()``, the read, the promotion, or ``close()``. So a
    marker that reads ``pending`` was left by a boot that never finished
    (killed, or interrupted while it cleaned up) or by a writer outside the
    SDK, and nothing shows that the store beside it was ever read. Such a marker
    is never read as a completed verification: every plain boot of the path,
    writer or read-only, is refused here, by name, before its store is booted,
    and the marker is left exactly as it is — never cleared automatically — for
    an operator to resolve (the security how-to, section 4.12, says what to
    inspect and what to remove). So is a marker that reads ``verified`` with no
    store beside it — its store was deleted or moved, and a store a boot created
    there now would be vouched for by a marker that never saw it — and so is a
    boot that cannot take the store-creation lock at all. Each is refused after
    registration and before anything is created at the path. The refusal states
    nothing the store holds.

    Attributes:
        marker: The deployment marker's path,
            ``<resolved store path>.ccf-deployment-store``.
        reason: Which check refused:

            * ``"pending"`` — the marker records a store creation whose
              emptiness read never completed;
            * ``"unreadable"`` — the marker records no state in the form the SDK
              writes: a marker written before markers recorded their state (one
              line), text the SDK did not write, a symbolic link, anything that
              is not a regular file, or a file this process cannot read;
            * ``"no-store"`` — the marker reads ``verified`` and no store stands
              beside it;
            * ``"claimed"`` — a marker appeared at the path after this boot
              looked and before it created its own, or the marker this boot
              created was replaced or rewritten before the boot could make it
              read ``verified``: something outside the SDK's boots writes
              beside the store;
            * ``"lock-unavailable"`` — the store-creation lock beside the marker
              cannot be opened or locked (no ``flock`` on this platform or
              filesystem, something other than a regular file at its path, or
              no permission).
        lock: The store-creation lock's path, for ``"lock-unavailable"``;
            ``None`` otherwise.
    """

    def __init__(
        self,
        *,
        marker: Path,
        reason: Literal["pending", "unreadable", "no-store", "claimed", "lock-unavailable"],
        lock: Path | None = None,
        detail: str | None = None,
    ) -> None:
        self.marker, self.reason, self.lock = marker, reason, lock
        what = f"the deployment marker {str(marker)!r} {_NOT_VERIFIED_WHY[reason]}"
        if lock is not None:
            what += f" ({str(lock)!r}: {detail or 'unavailable'})"
        super().__init__(
            f"DeploymentStoreNotVerified: {what}. No boot of that store proceeds until an operator resolves"
            f" it: {_NOT_VERIFIED_REMEDY[reason]} (the security how-to, section 4.12; SEC-020, D-IMPL-378)"
        )


class ManifestKeysPlaceToOneKey(ValueError):
    """Two manifest entries' keys place to ONE Control Plane key under the tenant.

    SDK-defined (CLAUDE.md §6.4 and §10), ``D-IMPL-378``. Placement
    (:func:`manifest_under_tenant`, ``D-IMPL-354``) writes a bare key ``k`` as
    ``{tenant}/k`` and leaves a key already written ``{tenant}/k`` unchanged, so
    two entries authored as ``k`` and ``{tenant}/k`` are distinct strings, which
    the contract's own key-uniqueness check admits, and ONE key once placed. One
    key holds one artifact in force. Placed anyway, the boot would keep one of the
    two documents and the register loop would register it under both entries.
    When both entries are of one class, the other document is never registered,
    pinned or returned, and nothing says so. Refused instead, by name, before
    anything is minted or registered, whatever the two entries' classes and
    roles, through every door that places keys (``load_and_boot``,
    ``load_config_and_boot`` and the consumer chain
    ``ccf.products.product.open_product`` derives).

    Attributes:
        authored_keys: The two keys as the manifest wrote them, in manifest order.
        placed_key: The one key both place to.
        tenant: The tenant they were placed under.
    """

    def __init__(self, *, authored_keys: tuple[str, str], placed_key: str, tenant: str) -> None:
        self.authored_keys, self.placed_key, self.tenant = authored_keys, placed_key, tenant
        first, second = authored_keys
        super().__init__(
            f"ManifestKeysPlaceToOneKey: manifest keys {first!r} and {second!r}"
            f" both place to {placed_key!r} under tenant {tenant!r}. A bare key"
            " and the same key written under the tenant are one Control Plane key"
            " once placed (D-IMPL-354), and one key holds one artifact in force:"
            " booting would register one of the two documents under both entries"
            " and drop the other with no record, so nothing is registered. Remove"
            " one entry, or give the two entries keys that differ once placed"
            " (D-IMPL-378)"
        )


def _store_paths(backend: str, connection: Mapping[str, object] | None) -> list[Path]:
    """Every path-valued setting of the adapter's own validated connection: the paths naming its store.

    SEC-020 (Q9, ``D-IMPL-378``). The lock-directory setting is set aside, as
    a read-only boot sets it aside: it names where writers take their lease,
    not where the graph is.
    """
    record = resolve(backend)
    config_model = record.registration.config_model
    validated = validate_connection(
        record.registration,
        _without_lock_directory_setting(config_model, connection or {}),
    )
    return [value for value in vars(validated).values() if isinstance(value, Path)]


#: SEC-020 P4 (a) (``D-IMPL-378``): what a boot for one question appends to the
#: resolved spelling of each path naming its store, to name the durable marker
#: it leaves there. Created exclusively, so it is also the boot's reservation
#: of the path.
_QUESTION_STORE_MARKER_SUFFIX = ".ccf-question-store"

#: SEC-020 P4 (a) made strict (``D-IMPL-378``; Dave, 2026-10-08 12:29 MST): what
#: any other boot that creates its store appends, so a store these doors
#: created for a deployment is told apart from an unmarked one.
_DEPLOYMENT_STORE_MARKER_SUFFIX = ".ccf-deployment-store"

_QUESTION_STORE_MARKER_TEXT = "booted for one question; it serves no later one (SEC-020, D-IMPL-378)\n"
_DEPLOYMENT_STORE_MARKER_TEXT = (
    "created by a boot not for a question; no acquisition phase writes into it (SEC-020, D-IMPL-378)\n"
)

#: SEC-020 repair 1.1 (``D-IMPL-378``; Dave, 2026-10-09 10:54 MST: *"A marker
#: left by a crash must not imply completed verification."*): the two states a
#: deployment marker records after the line above. A boot creates its marker
#: ``pending`` and makes it ``verified`` only once its emptiness read has
#: completed, so a marker a crash or an interrupted boot leaves never reads as a
#: completed verification.
_MARKER_PENDING = "pending"
_MARKER_VERIFIED = "verified"

#: The length, in hex characters, of the token a deployment marker carries: the
#: boot that created it, so a boot removes or promotes only its own marker.
_MARKER_TOKEN_HEX = 32


def _deployment_marker_text(state: str, token: str) -> str:
    """A deployment marker's whole text: the line every marker has carried, then its state and its boot's token."""
    return f"{_DEPLOYMENT_STORE_MARKER_TEXT}state: {state}\nboot: {token}\n"


@dataclass(frozen=True)
class _MarkerRecord:
    """What a deployment marker records, read back: its state and the token of the boot that created it."""

    state: str
    token: str


@dataclass(frozen=True)
class _OwnedMarker:
    """A deployment marker this boot created: its path, the token it wrote, and the file it is (device and inode)."""

    path: Path
    token: str
    device: int
    inode: int


def _sync_directory(directory: Path) -> None:
    """Sync ``directory``, so an entry created, replaced or removed in it survives a crash."""
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, text: str) -> None:
    """Write all of ``text`` to ``descriptor``."""
    data = text.encode("utf-8")
    while data:
        data = data[os.write(descriptor, data):]


def _unlink_if_same_file(path: Path, identity: tuple[int, int] | None) -> None:
    """Unlink ``path`` while it is still the file ``identity`` names (device and inode); ``None`` names whatever is there."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return
    if identity is None or (status.st_dev, status.st_ino) == identity:
        path.unlink(missing_ok=True)


def _read_deployment_marker(marker: Path) -> tuple[_MarkerRecord | None, tuple[int, int] | None]:
    """What the deployment marker at ``marker`` records, and which file it is (device and inode), through one descriptor.

    Opened without following a symbolic link and without blocking, and read
    only if it is a regular file no longer than the longest marker the SDK
    writes. The record is ``None`` for a marker an earlier tree wrote (one line,
    no state), text the SDK did not write, a symbolic link, anything that is not
    a regular file, and a file this process cannot read: none of them shows a
    completed verification. The identity is ``None`` when nothing could be
    opened.
    """
    longest = len(_deployment_marker_text(_MARKER_VERIFIED, "0" * _MARKER_TOKEN_HEX).encode("utf-8"))
    try:
        descriptor = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None, None
    identity: tuple[int, int] | None = None
    data = b""
    try:
        status = os.fstat(descriptor)
        identity = (status.st_dev, status.st_ino)
        if not stat.S_ISREG(status.st_mode):
            return None, identity
        while len(data) <= longest:
            chunk = os.read(descriptor, longest + 1 - len(data))
            if not chunk:
                break
            data += chunk
    except OSError:
        return None, identity
    finally:
        os.close(descriptor)
    if len(data) > longest:
        return None, identity
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, identity
    for state in (_MARKER_PENDING, _MARKER_VERIFIED):
        head = f"{_DEPLOYMENT_STORE_MARKER_TEXT}state: {state}\nboot: "
        token = text.removeprefix(head).removesuffix("\n")
        if (
            text.startswith(head)
            and text.endswith("\n")
            and len(token) == _MARKER_TOKEN_HEX
            and all(character in "0123456789abcdef" for character in token)
        ):
            return _MarkerRecord(state=state, token=token), identity
    return None, identity


def _create_pending_deployment_marker(path: Path) -> _OwnedMarker:
    """Create the deployment marker beside ``path`` exclusively, reading ``pending`` with a fresh token; file and directory synced.

    SEC-020 repair 1.1 (``D-IMPL-378``). ``O_CREAT | O_EXCL`` with
    ``O_NOFOLLOW``: of two creators exactly one succeeds, and the other meets
    :class:`FileExistsError`. From here the marker is this boot's: its token and
    its file (device and inode) are what :func:`_promote_deployment_marker` and
    :func:`_remove_deployment_marker_if_owned` check. A failure after the file
    exists removes it before propagating, so a marker this call could not
    finish writing is never left behind.
    """
    marker = _deployment_store_marker(path)
    token = os.urandom(_MARKER_TOKEN_HEX // 2).hex()
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    identity: tuple[int, int] | None = None
    try:
        try:
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
            _write_all(descriptor, _deployment_marker_text(_MARKER_PENDING, token))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _sync_directory(marker.parent)
    except BaseException:
        _unlink_if_same_file(marker, identity)
        raise
    return _OwnedMarker(path=marker, token=token, device=identity[0], inode=identity[1])


def _promote_deployment_marker(owned: _OwnedMarker) -> _OwnedMarker:
    """Make a marker this boot created read ``verified``, atomically, once its emptiness read has completed; return it.

    SEC-020 repair 1.1 (``D-IMPL-378``). The verified text is written to a
    staging file beside the marker, synced, and renamed over the marker
    (``os.replace``); the caller then syncs the directory. A crash at any
    instant leaves the marker reading ``pending`` or ``verified``, never part of
    either. A marker that is no longer the one this boot created (another file,
    or other text) is not replaced, and the boot is refused
    (:class:`DeploymentStoreNotVerified`, reason ``"claimed"``). The marker
    returned names the file that now stands at the path, for the removal a later
    failure would take.
    """
    record, identity = _read_deployment_marker(owned.path)
    if record is None or record.token != owned.token or identity != (owned.device, owned.inode):
        raise DeploymentStoreNotVerified(marker=owned.path, reason="claimed")
    staging = owned.path.with_name(f"{owned.path.name}.promoting-{owned.token}")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    staged: tuple[int, int] | None = None
    try:
        try:
            status = os.fstat(descriptor)
            staged = (status.st_dev, status.st_ino)
            _write_all(descriptor, _deployment_marker_text(_MARKER_VERIFIED, owned.token))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(staging, owned.path)
    except BaseException:
        _unlink_if_same_file(staging, staged)
        raise
    return _OwnedMarker(path=owned.path, token=owned.token, device=staged[0], inode=staged[1])


def _remove_deployment_marker_if_owned(owned: _OwnedMarker) -> None:
    """Remove a marker this boot created, only while it is still that file and still carries this boot's token.

    SEC-020 repair 1.1 (``D-IMPL-378``: *"Remove only markers this boot
    owns."*). The file's device and inode and its token are read through one
    descriptor, then the path is unlinked and its directory synced. A writer
    outside the SDK that replaces the file between that check and the unlink
    loses its file: the residual a path leaves, because POSIX offers no
    unlink-if-still-this-file call.
    """
    record, identity = _read_deployment_marker(owned.path)
    if record is None or record.token != owned.token or identity != (owned.device, owned.inode):
        return
    owned.path.unlink(missing_ok=True)
    _sync_directory(owned.path.parent)


#: SEC-020 repair 1.2 (``D-IMPL-378``; Dave, 2026-10-09 10:54 MST: *"Serialize
#: creation and verification"*): what a plain boot appends to the resolved
#: spelling of each path naming its store, to name the lock it holds from its
#: look at the path through the hand-back. Held for the boot, never for the
#: fabric's life. Not the SQLite writer lease (``<store>.ccf-writer.lock``,
#: held while a writer's fabric is open), and not a declared lock directory
#: (``writer_lease_lock_dir``).
_STORE_CREATION_LOCK_SUFFIX = ".ccf-store-creation.lock"


class _StoreCreationLock:
    """The store-creation locks of every path a plain boot names, taken in one order and held through the boot.

    SEC-020 repair 1.2 (``D-IMPL-378``). One exclusive ``flock`` per path, on
    ``<resolved path>.ccf-store-creation.lock`` (opened ``O_RDWR | O_CREAT |
    O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC``, mode ``0o600``, and only a regular
    file is locked), taken in sorted order, so two boots naming the same paths
    cannot deadlock. A ``flock`` belongs to an open file description, so it
    excludes another boot in another process and in another thread of this
    one, and the kernel drops it when its holder dies, however it dies: a
    crashed boot never wedges the next, whose look then finds the crashed
    boot's marker reading ``pending``. A boot that finds the lock held WAITS for
    it, with no timeout: another boot is creating or verifying the store, and
    when it has finished this boot sees what it left. A lock that cannot be
    opened or locked at all refuses the boot
    (:class:`DeploymentStoreNotVerified`, reason ``"lock-unavailable"``). A path
    whose directory does not exist takes no lock and is left to the adapter, as
    its marker is. The lock files stay beside their stores and vouch for
    nothing; removing one while no boot runs is harmless.
    """

    def __init__(self, paths: Sequence[Path]) -> None:
        locks = {
            Path(f"{path.resolve()}{_STORE_CREATION_LOCK_SUFFIX}"): path
            for path in paths
            if path.resolve().parent.is_dir()
        }
        self._locks = sorted(locks.items(), key=lambda item: str(item[0]))
        self._held: list[int] = []

    def acquire(self) -> None:
        """Take every lock, in order, waiting for each; refuse by name if one cannot be taken at all."""
        for lock, path in self._locks:
            try:
                if _fcntl is None:
                    raise OSError("this platform offers no flock")
                descriptor = os.open(
                    lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600
                )
            except OSError as unavailable:
                self.release()
                raise DeploymentStoreNotVerified(
                    marker=_deployment_store_marker(path), reason="lock-unavailable", lock=lock,
                    detail=unavailable.strerror or str(unavailable),
                ) from unavailable
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise OSError("not a regular file")
                _fcntl.flock(descriptor, _fcntl.LOCK_EX)
            except OSError as unavailable:
                os.close(descriptor)
                self.release()
                raise DeploymentStoreNotVerified(
                    marker=_deployment_store_marker(path), reason="lock-unavailable", lock=lock,
                    detail=unavailable.strerror or str(unavailable),
                ) from unavailable
            except BaseException:
                os.close(descriptor)
                self.release()
                raise
            self._held.append(descriptor)

    def release(self) -> None:
        """Release every lock held, in reverse order. Never raises: closing a descriptor drops its lock regardless."""
        held, self._held = self._held, []
        for descriptor in reversed(held):
            try:
                if _fcntl is not None:
                    _fcntl.flock(descriptor, _fcntl.LOCK_UN)
            except OSError:
                pass  # the close below drops the lock all the same
            try:
                os.close(descriptor)
            except OSError:
                pass  # the descriptor is released even when close reports an error


def _undo_a_failed_boot(
    failure: BaseException, *, handle: FabricHandle | None, created: Sequence[_OwnedMarker]
) -> None:
    """Close a failed boot's fabric and remove the markers it created that are still its own, never masking ``failure``.

    SEC-020 repair 1.1 (``D-IMPL-378``: *"Remove markers created by this boot on
    every failed-boot path, including failure during close."*). The markers are
    removed whatever ``close()`` does: an ``Exception`` from it, or from a
    removal, is recorded on ``failure`` as a note, so the caller meets the
    failure that refused the boot. A ``BaseException`` that is not an
    ``Exception`` (an interrupt) during this cleanup still runs the removals,
    then propagates in place of ``failure``; a marker it stops this cleanup from
    removing reads ``pending``, which no boot reads as a completed verification.
    """
    try:
        if handle is not None:
            try:
                handle.close()
            except Exception as closing:  # noqa: BLE001 — recorded on the failure, never raised over it
                failure.add_note(f"closing the fabric after this failure raised {closing!r}")
    finally:
        for owned in created:
            try:
                _remove_deployment_marker_if_owned(owned)
            except Exception as removing:  # noqa: BLE001 — recorded on the failure, never raised over it
                failure.add_note(f"removing the deployment marker {str(owned.path)!r} after this failure raised {removing!r}")


def _marker(path: Path, suffix: str) -> Path:
    """The marker ``suffix`` names beside ``path``, keyed on its resolved spelling, so two spellings of one store share it."""
    return Path(f"{path.resolve()}{suffix}")


def _question_store_marker(path: Path) -> Path:
    """The question marker beside ``path`` (SEC-020 P4 (a))."""
    return _marker(path, _QUESTION_STORE_MARKER_SUFFIX)


def _deployment_store_marker(path: Path) -> Path:
    """The deployment marker beside ``path`` (SEC-020 P4 (a) made strict)."""
    return _marker(path, _DEPLOYMENT_STORE_MARKER_SUFFIX)


def _create_marker_exclusively(marker: Path, text: str) -> None:
    """Create ``marker`` holding ``text`` only if nothing exists there, and make it durable.

    ``O_CREAT | O_EXCL``: of two boots creating one marker, exactly one
    succeeds and the other meets :class:`FileExistsError`. The file is synced
    and so is its directory, so the entry survives a crash as well as the
    process. What the filesystem raises propagates.
    """
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, text.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(marker.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _created_or_claimed_elsewhere(paths: Sequence[Path]) -> bool:
    """Whether a store, or another boot's deployment marker, exists at any path this boot has reserved."""
    return any(path.exists() or _deployment_store_marker(path).exists() for path in paths)


def _reserve_question_store(paths: Sequence[Path]) -> None:
    """Reserve every path naming a question's store for this boot alone, before the store exists.

    SEC-020 P4 (a) made strict (``D-IMPL-378``; Dave, 2026-10-08 12:29 MST:
    *"Require verifiable fresh creation"*). The freshness check ran before
    anything was registered; this is what makes it hold at the boot. Each
    question marker is created exclusively (:func:`_create_marker_exclusively`),
    so a second boot for a question at the same path — concurrent, or reusing a
    path whose marker was left behind — is refused here, and then no store and
    no other boot's deployment marker may exist at any path: a store created
    after the check is refused rather than booted "for one question". Written
    and synced BEFORE ``boot`` creates the store, so no store booted for a
    question exists without its marker. A refused reservation removes the
    markers this call created, and only those.

    Raises:
        QuestionFabricNotFresh: another boot holds a path, or a store (or
            another boot's deployment marker) appeared at one after the check.
    """
    reserved: list[Path] = []
    try:
        for path in paths:
            marker = _question_store_marker(path)
            try:
                _create_marker_exclusively(marker, _QUESTION_STORE_MARKER_TEXT)
            except FileExistsError:
                raise QuestionFabricNotFresh(
                    "a fabric booted for one question must be a fresh one, and"
                    " another boot already reserved the store this boot names"
                    " (its question marker exists), so two questions would"
                    " share it (SEC-020, Q9)"
                ) from None
            reserved.append(marker)
        if _created_or_claimed_elsewhere(paths):
            raise QuestionFabricNotFresh(
                "a fabric booted for one question must be a fresh one, and the"
                " store this boot names was created, or claimed by another"
                " boot, after its freshness was checked (SEC-020, Q9)"
            )
    except BaseException:
        for marker in reserved:
            marker.unlink(missing_ok=True)
        raise


def _mark_deployment_store(paths: Sequence[Path], created: list[_OwnedMarker]) -> bool:
    """Refuse where safe verification cannot be established; mark ``pending`` every path whose store this boot creates.

    SEC-020 P4 (a) made strict, and repairs 1.1 and 1.2 (``D-IMPL-378``).
    Called with the store-creation lock of every path held
    (:class:`_StoreCreationLock`), so no other boot of these paths is creating
    or verifying a store while it looks. A path whose deployment marker does not
    record a completed verification — ``pending`` (its boot never finished its
    read: it was killed, or interrupted) or no state in the SDK's form — is
    refused by name (:class:`DeploymentStoreNotVerified`), and so is a marker
    that reads ``verified`` with no store beside it; each is left for an
    operator. A path with no store and no marker of either kind names a store
    this boot creates, so the marker goes first, created exclusively and
    reading ``pending`` (:func:`_create_pending_deployment_marker`), and joins
    ``created`` at once, so a failure anywhere after it removes it; a marker that
    appears there before the exclusive create was made outside the SDK's
    boots, and is refused (``"claimed"``). A path whose directory is absent is
    left to the adapter, which creates the store or refuses it. A path holding a
    store, or a question marker, is read as it stands: never marked after the
    fact, because a marker written beside a store that already exists would
    vouch for contents this boot did not create.

    Returns whether this boot creates a store — a path held no store when it
    looked — which it must find empty, whoever made a marker beside the path
    (OWED-RULINGS-3 item 2A (b) and repair 1.2,
    :class:`DeploymentStoreNotEmpty`).
    """
    creates_a_store = False
    for path in paths:
        marker = _deployment_store_marker(path)
        if os.path.lexists(marker):
            record, _identity = _read_deployment_marker(marker)
            if record is None:
                raise DeploymentStoreNotVerified(marker=marker, reason="unreadable")
            if record.state != _MARKER_VERIFIED:
                raise DeploymentStoreNotVerified(marker=marker, reason="pending")
            if not path.exists():
                raise DeploymentStoreNotVerified(marker=marker, reason="no-store")
            continue
        if path.exists():
            continue
        creates_a_store = True
        if not path.resolve().parent.is_dir() or _question_store_marker(path).exists():
            continue
        try:
            created.append(_create_pending_deployment_marker(path))
        except FileExistsError:
            raise DeploymentStoreNotVerified(marker=marker, reason="claimed") from None
    return creates_a_store


def _marked_for_a_question(paths: Sequence[Path]) -> bool:
    """Whether a question boot left its marker beside any path naming this store (SEC-020 P4 (a))."""
    return any(_question_store_marker(path).exists() for path in paths)


def _store_creation(paths: Sequence[Path]) -> Literal["verified", "unmarked", "unverifiable"]:
    """What :attr:`BootedFabric.store_creation` reads: from the markers beside the store, never its contents.

    Read when the boot hands the fabric back, after its emptiness read and
    after the markers it created were made to read ``verified`` — never before
    (repair 1.1, ``D-IMPL-378``): ``"verified"`` needs, beside every path, a
    question marker or a deployment marker that records a completed
    verification.
    """
    if not paths:
        return "unverifiable"
    for path in paths:
        if _question_store_marker(path).exists():
            continue
        record, _identity = _read_deployment_marker(_deployment_store_marker(path))
        if record is None or record.state != _MARKER_VERIFIED:
            return "unmarked"
    return "verified"


def _names_a_path(annotation: object) -> bool:
    """Whether a contract field's annotation admits a path: a ``PurePath`` type, or a union or annotation over one."""
    origin = get_origin(annotation)
    if origin is Annotated:
        return _names_a_path(get_args(annotation)[0])
    if origin is Union or origin is types.UnionType:
        return any(_names_a_path(member) for member in get_args(annotation))
    return isinstance(annotation, type) and issubclass(annotation, PurePath)


def _path_valued_settings(backend: str) -> frozenset[str]:
    """The settings of ``backend``'s own connection contract that take a path: where a store can be minted fresh.

    SEC-020 P4 (a) made strict (``D-IMPL-378``). Read from the declared
    contract, never from a value, so it can be asked before anything is
    minted or booted: a substrate the paved road mints per question goes into
    one of these, or the SDK cannot verify the question's store fresh. The
    lock-directory setting is set aside, as :func:`_store_paths` sets it
    aside.
    """
    fields = resolve(backend).registration.config_model.model_fields
    return frozenset(
        name
        for name, field in fields.items()
        if name != _LOCK_DIRECTORY_SETTING and _names_a_path(field.annotation)
    )


def _refuse_unless_fresh(backend: str, paths: Sequence[Path]) -> None:
    """Raise :class:`QuestionFabricNotFresh` unless the adapter's connection names only paths that do not exist yet."""
    if not paths:
        raise QuestionFabricNotFresh(
            f"a fabric booted for one question must be a fresh one, and the"
            f" {backend!r} adapter's connection names no path whose absence"
            " could show it fresh (SEC-020, Q9)"
        )
    if any(path.exists() for path in paths):
        raise QuestionFabricNotFresh(
            "a fabric booted for one question must be a fresh one, and the"
            " store this boot names already exists — another question may have"
            " written into it (SEC-020, Q9)"
        )


#: SEC-020 P4s-A (b) (``D-IMPL-378``): the instant a question boot's one
#: emptiness read is taken at, the latest a timestamp can name. An as-of read
#: returns the claims observed at or before its instant and not superseded by
#: it, so at this instant it returns every claim of the tenant's that has no
#: successor, whenever it was observed: the newest claim of every entity and
#: relationship, which an SDK writer never supersedes without one.
_EMPTINESS_READ_AT = datetime.max.replace(tzinfo=UTC)


def _refuse_unless_empty(reader: GraphReader, *, tenant_id: str, for_question: bool) -> None:
    """Read a store this boot created once, through the governed reader, and refuse it unless it holds nothing for ``tenant_id``.

    SEC-020 P4s-A (b) (``D-IMPL-378``; Dave, 2026-10-08 16:40 MST) for a boot
    for a question, and OWED-RULINGS-3 item 2A (b) (Dave, 2026-10-09 06:21 MST)
    for a plain boot that created its deployment marker. One ``as_of`` read at
    :data:`_EMPTINESS_READ_AT`, through the Protocol every adapter answers: no
    Protocol change and no adapter-specific query. The refusal states no count
    and nothing the store holds.

    Raises:
        QuestionStoreNotEmpty: ``for_question``, and the view holds an entity
            or a relationship.
        DeploymentStoreNotEmpty: a plain boot, and the view holds one.
    """
    view = reader.as_of(tenant_id=tenant_id, at=_EMPTINESS_READ_AT)
    if not (view.entities or view.relationships):
        return
    if for_question:
        raise QuestionStoreNotEmpty(
            "a fabric booted for one question must be a fresh one, and the"
            " store it opened already holds claims for its tenant: something"
            " other than this question wrote into it at its path before the"
            " boot returned (SEC-020, P4)"
        )
    raise DeploymentStoreNotEmpty(
        "a boot that creates its store must find it empty, and the store it"
        " opened already holds claims for its tenant: something other than"
        " this boot wrote into it at its path before the boot returned, so"
        " nothing vouches for it (SEC-020, OWED-RULINGS-3 2A (b))"
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
    paths = _store_paths(manifest.backend, connection)
    if for_question:
        # SEC-020 P4s-A (b) (`D-IMPL-378`; Dave, 2026-10-08 16:40 MST: *"The
        # check must precede acquisition and remain protected by exclusive
        # ownership through use."*): what holds a question's store from its
        # emptiness check to the question's end is the question marker and the
        # writer lease, and a read-only boot takes no lease. Refused here,
        # before anything is registered or created at the path.
        if read_only:
            raise QuestionFabricNotExclusive(
                "a fabric booted for one question holds its store from its"
                " emptiness check to the question's end through its writer"
                " lease, and a read-only boot takes none: another boot could"
                " write into the store while the question reads it (SEC-020, P4)"
            )
        _refuse_unless_fresh(manifest.backend, paths)
    manifest, parsed, keys = manifest_under_tenant(manifest, parsed, keys, tenant=resolved_tenant)
    # SEC-023 (`D-IMPL-372`): before anything is registered or minted, a
    # deployment whose Policy operator admits on a source-asserted attribute
    # with no declared authority refuses to boot, by name.
    _refuse_ungoverned_classification(manifest, parsed)
    # Phase two: register the ones the manifest marks `role: register`.
    pinned = register_manifest_entries(manifest, parsed, registry=registry, tenant=resolved_tenant)
    pins = ResolvedPins(entries=pinned)
    # SEC-020 P4 (a) (`D-IMPL-378`): the marker BEFORE the boot creates the
    # store, so a question's store never exists without it; and every boot
    # reads it, so a later boot of that store knows it is one
    # (`BootedFabric.question_store`). Made strict (Dave, 2026-10-08 12:29 MST:
    # *"Require verifiable fresh creation"*): a question boot's marker is its
    # exclusive reservation of the path, and any other boot that creates its
    # store marks it too, so an existing store with neither marker is unmarked
    # and never presumed fresh (`BootedFabric.store_creation`).
    # Repair 1.1 (`D-IMPL-378`; Dave, 2026-10-09 10:54 MST: *"Remove markers
    # created by this boot on every failed-boot path, including failure during
    # close. Remove only markers this boot owns. A marker left by a crash must
    # not imply completed verification."*): ONE span, from the first marker
    # this boot creates to the hand-back. A deployment marker is created
    # reading `pending`, carrying this boot's token, and joins `created` at
    # once; it is made to read `verified` only after the emptiness read has
    # completed; and any failure in the span — `boot()`, the read, the
    # promotion, building the fabric, or an interrupt — closes the handle and
    # removes the markers that are still this boot's own, whatever `close()`
    # does (`_undo_a_failed_boot`). A question marker stays, as before.
    # Repair 1.2 (Dave, 2026-10-09 10:54 MST: *"Run the emptiness check
    # whenever a plain boot creates a new store. Serialize creation and
    # verification ... If safe verification cannot be established, refuse until
    # an operator resolves the stale marker."*): a plain boot holds the
    # store-creation lock of every path from its look through the hand-back, so
    # a boot that finds another creating the store waits for it; its look
    # refuses what it cannot verify safely; and every plain boot whose path held
    # no store takes the read, whoever made a marker there. A question boot's
    # path is held by its exclusive question marker instead, as before.
    created: list[_OwnedMarker] = []
    handle: FabricHandle | None = None
    lock = _StoreCreationLock(() if for_question else paths)
    lock.acquire()
    try:
        if for_question:
            _reserve_question_store(paths)
            creates_a_store = True
        else:
            creates_a_store = _mark_deployment_store(paths, created)
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
        if creates_a_store:
            # SEC-020 P4s-A (b) (`D-IMPL-378`; Dave, 2026-10-08 16:40 MST: *"Add
            # the emptiness check ... The check must precede acquisition and
            # remain protected by exclusive ownership through use."*): the store
            # the adapter opened is read once, here, after `boot` took the writer
            # lease and before the fabric is handed back, so before any
            # acquisition phase or governed call can run over it. A store holding
            # anything for the tenant is closed and refused; its question marker
            # stays, so the path keeps refusing.
            # OWED-RULINGS-3 item 2A (b) (Dave, 2026-10-09 06:21 MST), with the
            # trigger repair 1.2 restores: a plain boot whose path held no store
            # is creating a new store, so it takes the same one read, whoever
            # made a marker there. Refused, it removes the markers it created,
            # so no marker vouches for the store; a boot that reopens a store
            # takes no read.
            _refuse_unless_empty(handle.reader, tenant_id=resolved_tenant, for_question=for_question)
        # Repair 1.1: only now, the read completed, does a marker this boot
        # created read `verified` — atomically, then durably.
        for index, owned in enumerate(created):
            created[index] = _promote_deployment_marker(owned)
            _sync_directory(owned.path.parent)
        return BootedFabric(
            handle=handle,
            pins=pins,
            tenant_id=resolved_tenant,
            artifacts=parsed,
            survivor_cap=manifest.survivor_cap,
            keys=keys,
            for_question=for_question,
            question_store=_marked_for_a_question(paths),
            store_creation=_store_creation(paths),
        )
    except BaseException as failure:
        _undo_a_failed_boot(failure, handle=handle, created=created)
        raise
    finally:
        lock.release()


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

    The derivation is many-to-one — a bare ``k`` and ``{tenant}/k`` place to
    the same key — and the parsed mapping it re-keys holds one document per
    key. So two of the manifest's entries placing to one key are refused here,
    from the entries rather than from ``parsed`` (which a caller may pass
    partial), before anything is re-keyed (``D-IMPL-378``).

    Raises:
        ManifestKeysPlaceToOneKey: two entries' keys place to one key under
            ``tenant``, whatever their classes and roles.
    """

    def under(key: str) -> str:
        return namespaced_key(tenant=tenant, key=key)

    # `D-IMPL-378`: BEFORE the re-keying below, whose mapping would keep one of
    # two colliding documents and hand the register loop the survivor for both
    # entries. Every door that places keys reaches this before it mints.
    authored_by_placed: dict[str, str] = {}
    for entry in manifest.artifacts:
        placed = under(entry.key)
        if placed in authored_by_placed:
            raise ManifestKeysPlaceToOneKey(
                authored_keys=(authored_by_placed[placed], entry.key),
                placed_key=placed,
                tenant=tenant,
            )
        authored_by_placed[placed] = entry.key

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

    Raises:
        ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstantMisplaced:
            the manifest declares a demonstration serve instant the composition
            would never read — at a key other than the tenant's derived one —
            refused before anything is registered (`D-IMPL-378` C1).
    """
    # `D-IMPL-378` C1 (SDK-defined, CLAUDE.md §11), BEFORE the loop: a
    # demonstration serve instant is read from ONE key per tenant, so one
    # declared anywhere else would boot and silently do nothing. Over every
    # entry of the class, whatever `only` names — this is the one loop both boot
    # doors and the paved road run, and a composition root may call it directly.
    # Two entries at one key never get here: `manifest_under_tenant` refuses them
    # for every class (`ManifestKeysPlaceToOneKey`).
    refuse_misplaced_demonstration_serve_instants(
        keys=[
            entry.key
            for entry in manifest.artifacts
            if entry.class_id == DEMONSTRATION_SERVE_INSTANT.class_id
        ],
        tenant_id=tenant,
    )
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
            (:class:`QuestionFabricNotFresh` otherwise), read once when the
            boot returns and refused if it holds anything for the tenant
            (:class:`QuestionStoreNotEmpty`, P4s-A (b)), and the returned
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
            and pin under an SDK class name (D-IMPL-84), as
            :class:`~ccf.controlplane.artifact_base.ReservedArtifactClassId`
            (OWED-RULINGS-3 item 3P2 (b)); or a
            ``registration: versioned`` entry was
            refused by the D-05 hash-verified bump check. That last one is a
            **returned** refusal from :meth:`register_versioned
            <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>`
            turned into a loud failure here, naming the key, the class and the
            refusal type: a refusal is never swallowed, never downgraded to a
            warning, and never retried down the ``typed`` path.
        ManifestKeysPlaceToOneKey: two entries' keys place to one key under
            the resolved tenant (a bare ``k`` beside ``{tenant}/k``), whatever
            their classes and roles. A ``ValueError``, raised after every
            document is parsed and before anything is minted or registered
            (``D-IMPL-378``).
        QuestionFabricNotFresh: ``for_question=True`` over a store the boot
            cannot show fresh — its connection names no path, a path already
            exists or another boot reserved it — or, as
            :class:`QuestionStoreNotEmpty`, a store that held anything for the
            tenant when the boot returned, whose handle is closed before the
            refusal; or, as :class:`QuestionFabricNotExclusive`,
            ``read_only=True`` beside it, before anything is registered
            (SEC-020, ``D-IMPL-378``). A ``ValueError``.
        DeploymentStoreNotEmpty: a boot not for a question that creates its
            store — a path naming it held no store when the boot looked,
            whoever made a marker beside it — opened a store that held
            anything for the tenant when the boot returned; its handle is
            closed and the markers it created are removed before the refusal
            (SEC-020, ``D-IMPL-378`` OWED-RULINGS-3 item 2A (b), with the
            trigger repair 1.2 restores). A ``ValueError``.
        DeploymentStoreNotVerified: a boot not for a question where safe
            verification cannot be established, raised after registration
            and before anything is created at the path: a deployment marker
            that reads ``pending`` (the boot that created it never finished
            its read) or records no state in the form the SDK writes (a
            marker written before markers recorded their state included),
            one that reads ``verified`` with no store beside it, one that
            appeared or changed while this boot held the store-creation lock,
            or a store-creation lock that cannot be taken; its ``reason`` says
            which. The marker is left as it stands, for an operator (SEC-020,
            ``D-IMPL-378`` repairs 1.1 and 1.2). A ``ValueError``.
        UngovernedClassificationAttribute: a Policy operator the manifest
            names admits on a source-asserted classification attribute that
            no declared authority governs (SEC-023, ``D-IMPL-372``); raised
            before anything is registered or minted. A ``ValueError``.
        ccf.graph._writer.SingleWriterViolation: a writer boot of a graph that
            already has a live writer, in this process or, under the store's
            cross-process writer lease, in another (SEC-013; raised by
            :func:`ccf.boot.boot`); the markers this boot created are removed
            before it propagates. A read-only boot is never refused for one.
            A ``RuntimeError``.
        ccf.graph.protocols.WriterLeaseHeld: the SQLite store refuses to open
            a database file that has more than one name (a hard link), for a
            writer boot and a read-only boot alike, before any setup
            (SEC-013, P2 (b), ``D-IMPL-378``); the markers this boot created
            are removed before it propagates. A ``RuntimeError``.
        ccf.graph.protocols.WriterLeaseRequired: a writer boot of a persistent
            network store that declares no writer lease (SEC-013; raised by
            :func:`ccf.boot.boot`). A ``RuntimeError``.
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
        ccf.controlplane.artifacts.ArtifactClassIdMismatch: an entry's
            document states a ``class_id`` other than the class the entry
            names, whatever the entry's role. A ``ValueError``, raised while
            every document is parsed, before anything is minted or registered
            (``D-IMPL-378``).
        OSError: the manifest or a named artifact document cannot be read.
        BaseException: whatever the declared adapter's own store or writer
            constructor raises, re-raised unchanged after the markers this boot
            created are removed — for the SQLite adapter, SQLite's own error
            for a path whose directory does not exist
            (``sqlite3.OperationalError``).
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
