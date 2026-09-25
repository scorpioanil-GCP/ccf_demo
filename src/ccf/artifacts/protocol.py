"""``ArtifactStoreProtocol`` — content-addressed artifact persistence.

SDK-defined (CLAUDE.md §7.4); DESIGN.md §8.4; addressing per the D-IMPL-26
ruling.

**Hybrid addressing.** Canonical identity is ``sha256(canonical_bytes(artifact))``
— the same content-address primitive the whole SDK uses, so an artifact's
identity is computable by anyone holding the artifact and requires trusting no
store. On top of that sits a versioned URI for naming:

    ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}

with ``artifact_version`` being the content address. ``@latest`` is permitted
only at authoring surfaces: **a replay record or lineage entry never stores
"latest", it stores the hash.** This Protocol has no surface that could return
"whatever is newest under this name", which is how that rule survives contact
with a hurried caller.

**Immutability.** Content addressing makes overwrite meaningless — writing the
same bytes twice yields the same address, and writing different bytes yields a
different one. An implementation therefore never needs, and must never offer,
an update or delete operation. That is what makes the tampering threat
(T-04-11) structural rather than procedural.

**A write requires the capability for its own action (D-IMPL-353 §1.2).**
``put(authorized, artifact)`` takes no tenant, no class and no name from its
caller. Which kind it requires is looked up **per artifact class** from a
:class:`WriteKinds` declaration bound to the store at composition: a class the
deployment has not declared is the *client lane* and requires
``Authorized[ArtifactWrite]`` whose resource IS the target,
``"<class>/<name>"``; a class the deployment has declared is *mechanism
written* and requires one of the kinds declared for it — the fabric's replay
writer under ``ReplayMint`` (§2 P3; minted only at composition, so no served
surface can obtain one), the workflow engine's trace under ``Execute |
Resume``. The kind IS the mint: there is no separate token, no minting
handle, and no default that leaves a class open — ``write_kinds`` has no
default, and a declaration may not name ``ArtifactWrite``. The tenant is the
capability's on every path (§1.3). :func:`authorized_write_target` is the one
function both shipped stores run first, before canonicalization, before the
address is derived and before the substrate is touched; it is where
``ccf.controlplane.state.verify_any`` refuses a fabricated, retargeted or
wrong-kind capability, and where the target is resolved from the capability
(an addressed write) or from the mechanism's own :class:`DerivedWrite` (a
derived write — the record did not exist when the decision was made).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Final, Protocol, TypeAlias, runtime_checkable

from ccf.authz.capability import (
    ActionKind,
    ArtifactWrite,
    Authorized,
    Execute,
    ReplayMint,
    Resume,
)
from ccf.contracts.base import CCFContract
from ccf.controlplane.state import verify_any

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARTIFACT_URI_SCHEME",
    "CONTENT_ADDRESS_PATTERN",
    "LATEST_VERSION_TOKEN",
    "NAME_SEGMENT_SEPARATOR",
    "ArtifactName",
    "ArtifactNotFound",
    "ArtifactRef",
    "ArtifactStoreError",
    "ArtifactStoreProtocol",
    "ArtifactUriUnresolvable",
    "ArtifactWriteAuthority",
    "ArtifactWriteRefused",
    "DerivedWrite",
    "MalformedContentAddress",
    "MovingTargetRefused",
    "WriteKinds",
    "WriteKindsDeclarationError",
    "WriteTarget",
    "artifact_uri",
    "authorized_write_target",
    "held_content_address",
    "parse_artifact_uri",
]

ARTIFACT_URI_SCHEME = "ccf-artifact"

#: The one token a versioned URI may never resolve. Named here so the refusal
#: is a single, greppable fact rather than a string literal repeated at each
#: resolver (CLAUDE.md §7.4: replay resolves exact versions, never "latest").
LATEST_VERSION_TOKEN = "latest"


class ArtifactStoreError(Exception):
    """Base of the store's typed failures.

    Typed rather than bare so a caller can distinguish "the artifact this
    decision was recorded against is not here" from "the substrate is
    unreachable". The two demand opposite responses, and a replay that
    conflated them would report a missing record as an outage.
    """


class ArtifactNotFound(ArtifactStoreError, KeyError):
    """Nothing is stored at the requested content address.

    Also a ``KeyError``, so callers written against the mapping-shaped reading
    of :meth:`ArtifactStoreProtocol.get` keep working.
    """


class MalformedContentAddress(ArtifactNotFound):
    """The string asked for is not a content address, so nothing is stored at it.

    ``D-IMPL-345`` (`S-02`). A content address is ``sha256(canonical_bytes)``
    rendered as 64 lowercase hex characters and is nothing else. A store whose
    read path accepts an arbitrary string accepts a *path*: the measured
    consequences on the file-backed store were a traversal
    (``../../../../etc/hostname`` read the host's file) and a read of the
    store's own naming index at ``.artifact-names.json``, which enumerates
    every tenant, class, name and address the store holds.

    **A subclass of** :class:`ArtifactNotFound`, deliberately, on two counts.
    It is *true*: no artifact can be stored at a string that cannot be an
    address. And it keeps the refusal indistinguishable from an absent
    artifact for every caller that already catches ``ArtifactNotFound`` — a
    malformed address that answered differently from an unused one would be an
    existence oracle at every door at once (``D-IMPL-253`` amendment 2 (4)).
    A caller that wants the distinction for its own diagnostics can still
    catch this type by name.
    """


class ArtifactUriUnresolvable(ArtifactStoreError, LookupError):
    """A versioned URI names no artifact version this store registered.

    Raised — never softened into a nearby version, and never into the newest
    one under the name. An unresolvable URI in a replay means the replay cannot
    proceed, which is the correct outcome (D-IMPL-26).
    """


class MovingTargetRefused(ArtifactStoreError, ValueError):
    """A URI asked for ``@latest``.

    Distinct from :class:`ArtifactUriUnresolvable` because the caller is not
    missing an artifact; the caller asked a question the store must never
    answer. The URI is a string, so this is the only place the moving target
    can be refused.
    """


class ArtifactWriteRefused(ArtifactStoreError):
    """A write's *target* could not be resolved from what was presented (D-IMPL-353 §1.2).

    Raised **after** the capability has been verified genuine — a fabricated,
    retargeted or wrong-kind capability never reaches this refusal; it dies in
    ``verify`` first — for the shapes a genuine capability still cannot
    write: an addressed write whose resource is not ``"<class>/<name>"``, or
    a :class:`DerivedWrite` naming a class the deployment never declared as
    mechanism-written (which would let a door's ``ArtifactWrite`` capability
    pick a name other than its own resource's). Nothing has been
    canonicalized and nothing has been touched when it is raised.

    **Not an** :class:`ArtifactNotFound`: a refused write is a determination,
    not an absence, and typing it as absence would be swallowed by every
    ``except ArtifactNotFound`` written for the read path.
    """


class WriteKindsDeclarationError(ArtifactStoreError):
    """A :class:`WriteKinds` declaration could not be enforced (D-IMPL-353 §1.2).

    Raised at declaration — at boot, where an operator sees it — never at
    request time: an unusable declaration is a misconfiguration, not a
    decision about any caller.
    """


class ArtifactName(CCFContract):
    """The naming half of a parsed versioned URI (D-IMPL-26).

    Attributes:
        tenant_id: Owning tenant.
        artifact_class: Which class of artifact the name lives in.
        name: The logical name within the class.
        artifact_version: The requested version — a content address.
    """

    tenant_id: str
    artifact_class: str
    name: str
    artifact_version: str


#: What a content address is, and the whole of it (``D-IMPL-26``): the
#: lowercase hexadecimal sha256 digest :func:`~ccf.contracts.canonical.content_hash`
#: produces. Stated once, here, beside the addressing rule — a store that
#: spelled its own check would let two implementations disagree about what an
#: address is, and the one that disagreed downward would be a path reader.
CONTENT_ADDRESS_PATTERN: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{64}\Z")


def held_content_address(content_address: str) -> str:
    """Return ``content_address`` if it is one; otherwise refuse (``S-02``).

    The ONE shape check every store's read path runs **before it touches its
    substrate**. It is deliberately total rather than a list of dangerous
    shapes: an address either matches :data:`CONTENT_ADDRESS_PATTERN` or it is
    not an address, which refuses ``..`` traversal, absolute paths, the naming
    index's own filename, uppercase digests, truncated digests, the empty
    string and every other malformed string in one invariant, without any of
    them being named. Naming them one at a time is how a filter acquires a
    hole (``D-IMPL-345`` `S-02`: *"Do not special-case `/etc/hostname`, HTTP
    paths, or MCP paths"*).

    Placed on the Protocol module rather than in a door because the doors are
    not where the substrate is touched: HTTP, the MCP artifact resources, the
    CLI and in-process replay all reach a store's ``get``, and a check at one
    door leaves the others reading paths.

    Args:
        content_address: What a caller asked for.

    Returns:
        The address, unchanged, so a call site reads
        ``target = self._path(held_content_address(content_address))``.

    Raises:
        MalformedContentAddress: it is not a content address. An
            :class:`ArtifactNotFound` subclass, so a caller that already
            handles absence handles this identically.
    """
    if not CONTENT_ADDRESS_PATTERN.match(content_address):
        raise MalformedContentAddress(content_address)
    return content_address


#: The character the versioned URI and every naming index use to separate
#: ``tenant / class / name``. Named once so the reason a governed class id may
#: not contain it (below) is a fact about the grammar rather than a taste.
NAME_SEGMENT_SEPARATOR: Final[str] = "/"


class WriteKinds:
    """Which action kinds may write each *mechanism-written* artifact class (D-IMPL-353 §1.2).

    **The deployment declares, mechanism interprets.** The SDK cannot name the
    replay record class, the query-pin class or the workflow-trace class —
    :mod:`ccf.replay.serve` has always called them *"deployment vocabulary,
    supplied rather than assumed"*, and a class list in ``/src`` would be the
    hardcoding CLAUDE.md §6.4 forbids. So the deployment states, once, at
    composition: *these classes are written by fabric mechanism, under these
    kinds*. Everything undeclared is the client lane and requires
    ``Authorized[ArtifactWrite]`` for exactly ``"<class>/<name>"``.

    **Two lanes, and no class is in both.** A declaration may not name
    ``ArtifactWrite``: the client kind is what an *undeclared* class requires,
    and a class that both a door and mechanism could file under would be the
    ``SEC-004`` naming lane reopened. A declared class therefore admits only
    derived writes (:class:`DerivedWrite`) under its declared kinds; an
    undeclared class admits only addressed writes under ``ArtifactWrite``.

    **No default.** Both shipped stores take ``write_kinds`` as a required
    constructor argument. A store whose replay class is undeclared refuses the
    fabric's own ``ReplayMint`` writer at first use — wrong kind — which is
    the loud boot-time failure ``create_app`` is meant to surface (§3), never
    a silently open lane.

    **Membership is exact.** No casefolding, no trimming. A class id is refused
    at declaration if it is empty, untrimmed, or carries
    :data:`NAME_SEGMENT_SEPARATOR` — the naming key is
    ``f"{tenant}/{artifact_class}/{name}"``, so a slash-free id admits exactly
    one ``(tenant, class, name)`` decomposition of a target, while
    ``class="a/b", name="x"`` and ``class="a", name="b/x"`` collide on
    ``t/a/b/x``; the rule is measured, not stylistic.
    """

    __slots__ = ("_kinds_by_class",)

    def __init__(self, kinds_by_class: Mapping[str, tuple[type[ActionKind], ...]]) -> None:
        for class_id, kinds in kinds_by_class.items():
            if not class_id or class_id != class_id.strip():
                raise WriteKindsDeclarationError(
                    f"{class_id!r} is not a usable artifact class id; a declared"
                    " class must be a non-empty string with no surrounding"
                    " whitespace, because an id that does not match the string"
                    " the fabric writes governs nothing and says nothing"
                )
            if NAME_SEGMENT_SEPARATOR in class_id:
                raise WriteKindsDeclarationError(
                    f"{class_id!r} contains {NAME_SEGMENT_SEPARATOR!r}, so a"
                    " client could reach its naming lane by splitting the id"
                    " across the class and the name; declare a class id that is"
                    " one naming segment (SEC-004; D-IMPL-353 §1.2)"
                )
            if not kinds:
                raise WriteKindsDeclarationError(
                    f"class {class_id!r} declares no write kind; a declared"
                    " class is mechanism-written and must name the kind(s)"
                    " that write it (D-IMPL-353 §1.2)"
                )
            for kind in kinds:
                if not (isinstance(kind, type) and issubclass(kind, ActionKind)):
                    raise WriteKindsDeclarationError(
                        f"class {class_id!r} declares {kind!r}, which is not an"
                        " action kind (D-IMPL-353 §1.5b)"
                    )
                if kind is ArtifactWrite:
                    raise WriteKindsDeclarationError(
                        f"class {class_id!r} declares ArtifactWrite; the client"
                        " kind is what an UNDECLARED class requires, and a class"
                        " both a door and mechanism could file under is the"
                        " naming lane SEC-004 closed (D-IMPL-353 §1.2)"
                    )
        self._kinds_by_class: dict[str, tuple[type[ActionKind], ...]] = {
            class_id: tuple(kinds) for class_id, kinds in kinds_by_class.items()
        }

    @classmethod
    def declare(
        cls, kinds_by_class: Mapping[str, Iterable[type[ActionKind]]]
    ) -> WriteKinds:
        """Declare the mechanism-written classes and their kinds.

        The documented constructor::

            WriteKinds.declare({
                "ccf.replay-record": (ReplayMint,),
                "ccf.graph-query": (ReplayMint,),
                "ccf.workflow-trace": (Execute, Resume),
            })
        """
        return cls({class_id: tuple(kinds) for class_id, kinds in kinds_by_class.items()})

    @property
    def declared_classes(self) -> frozenset[str]:
        """The mechanism-written classes, for introspection."""
        return frozenset(self._kinds_by_class)

    def is_declared(self, artifact_class: str) -> bool:
        """Whether ``artifact_class`` is mechanism-written."""
        return artifact_class in self._kinds_by_class

    def for_class(self, artifact_class: str) -> tuple[type[ActionKind], ...]:
        """The kinds that may write ``artifact_class``: its declaration, or ``(ArtifactWrite,)``."""
        return self._kinds_by_class.get(artifact_class, (ArtifactWrite,))

    def __repr__(self) -> str:
        declared = {c: tuple(k.__name__ for k in ks) for c, ks in sorted(self._kinds_by_class.items())}
        return f"WriteKinds({declared!r})"


class DerivedWrite:
    """An artifact the fabric's own mechanism files, naming its class and name itself (D-IMPL-353 §1.2).

    The *derived-writes* shape. A door-minted capability names its target —
    ``"<class>/<name>"`` — because the authorizer decided on that target. A
    decision that *started* something — an ``Execute`` for a workflow
    definition, a ``ReplayMint`` for a record class — could not name the
    record it would produce, so the mechanism that produces it (the engine
    for its trace, the replay writer for its record) names the class and the
    name here, and the store files it under the capability's tenant, after
    verifying the capability against the kinds the deployment declared for
    that class.

    Not a name parameter in disguise: a class that is not declared
    mechanism-written refuses this shape outright (:class:`ArtifactWriteRefused`),
    so a door holding ``ArtifactWrite`` for one target cannot use it to file
    under another name; and a declared class never admits ``ArtifactWrite``.

    Attributes:
        artifact_class: The declared class this is filed under.
        name: The logical name within the class — the record's own identity
            (a snapshot id, an execution id, a query's content hash), never a
            remote caller's string.
        artifact: The canonicalizable payload. The content address, the bytes
            and the canonical form are this value's alone; the wrapper never
            reaches the substrate.
    """

    __slots__ = ("artifact_class", "name", "artifact")

    def __init__(self, *, artifact_class: str, name: str, artifact: object) -> None:
        self.artifact_class = artifact_class
        self.name = name
        self.artifact = artifact

    def __repr__(self) -> str:
        return f"DerivedWrite(artifact_class={self.artifact_class!r}, name={self.name!r})"


class WriteTarget(CCFContract):
    """Where a verified write lands: the tenant is the capability's, the rest is resolved.

    Returned by :func:`authorized_write_target` only, so a store's ``put`` reads
    ``target = authorized_write_target(...)`` and then acts on the target and
    nothing it was handed directly.

    Attributes:
        tenant_id: ``authorized.tenant`` — the only source (§1.3).
        artifact_class: From the capability's resource (addressed) or the
            :class:`DerivedWrite` (derived).
        name: Likewise.
    """

    tenant_id: str
    artifact_class: str
    name: str


#: The static type of ``put``'s first parameter: the kinds under which the
#: SDK's own writers and the client door file artifacts. A handler holding any
#: other kind is a ``mypy --strict`` error at the call; the runtime authority
#: for a given class is the store's :class:`WriteKinds` declaration.
ArtifactWriteAuthority: TypeAlias = (
    Authorized[ArtifactWrite]
    | Authorized[ReplayMint]
    | Authorized[Execute]
    | Authorized[Resume]
)


def authorized_write_target(
    authorized: ArtifactWriteAuthority, artifact: object, *, write_kinds: WriteKinds
) -> tuple[WriteTarget, object]:
    """Verify the capability and resolve the write's target — the first statement of every ``put``.

    Order is load-bearing and is the order of the design's teeth:

    1. **Pure parsing only.** The class is read from the :class:`DerivedWrite`
       if that is the shape, else from the capability's resource split at its
       first :data:`NAME_SEGMENT_SEPARATOR`. Nothing is trusted yet.
    2. :func:`~ccf.controlplane.state.verify_any` against the kinds the
       declaration names for that class (``(ArtifactWrite,)`` for an
       undeclared one), with the capability's own resource as the resource
       bind. A fabricated, retargeted or wrong-kind capability dies here — the
       same line and the same exception whichever shape was presented.
    3. **Shape refusals**, now that the capability is known genuine: a derived
       write into an undeclared class, or an addressed write whose resource is
       not ``"<class>/<name>"``.

    Returns:
        The target under ``authorized.tenant``, and the payload to canonicalize
        (the artifact itself, or the derived write's inner artifact).

    Raises:
        ccf.authz.capability.CapabilityBypassError: from ``verify_any``.
        ArtifactWriteRefused: the target shape.
    """
    resource_value = getattr(authorized, "resource", None)
    resource = resource_value if isinstance(resource_value, str) else ""
    if isinstance(artifact, DerivedWrite):
        artifact_class, name, payload = artifact.artifact_class, artifact.name, artifact.artifact
        derived = True
    else:
        artifact_class, _, name = resource.partition(NAME_SEGMENT_SEPARATOR)
        payload = artifact
        derived = False
    kinds = write_kinds.for_class(artifact_class) if artifact_class else (ArtifactWrite,)
    verify_any(authorized, kinds=kinds, resource=resource)
    assert isinstance(authorized, Authorized)  # proven by verify_any
    if derived:
        if not write_kinds.is_declared(artifact_class):
            raise ArtifactWriteRefused(
                f"a derived write names class {artifact_class!r}, which this"
                " store does not declare mechanism-written; only a declared"
                " class admits the mechanism naming its own record, and a"
                " door's capability names its target in its resource"
                " (D-IMPL-353 §1.2)"
            )
        if not artifact_class or not name:
            raise ArtifactWriteRefused(
                "a derived write must name a class and a name (D-IMPL-353 §1.2)"
            )
    elif not artifact_class or not name:
        raise ArtifactWriteRefused(
            f"the capability's resource {resource!r} is not an artifact target;"
            f" an addressed write is authorized for '<class>{NAME_SEGMENT_SEPARATOR}<name>'"
            " and the store takes both from it (D-IMPL-353 §1.2, §1.5f)"
        )
    return (
        WriteTarget(tenant_id=authorized.tenant, artifact_class=artifact_class, name=name),
        payload,
    )


def artifact_uri(
    *, tenant_id: str, artifact_class: str, name: str, artifact_version: str
) -> str:
    """Render the D-IMPL-26 versioned URI for one artifact version."""
    return (
        f"{ARTIFACT_URI_SCHEME}://{tenant_id}/{artifact_class}/"
        f"{name}@{artifact_version}"
    )


def parse_artifact_uri(uri: str) -> ArtifactName:
    """Parse a versioned URI into its four naming components.

    Structural parsing only — this function does not know whether anything is
    stored. It exists so every implementation of the Protocol agrees about what
    a URI *means* rather than each re-deriving it, which is how two stores
    would drift into resolving the same string differently.

    Raises:
        MovingTargetRefused: the version is ``latest``.
        ArtifactUriUnresolvable: the string is not a well-formed artifact URI.
    """
    prefix = f"{ARTIFACT_URI_SCHEME}://"
    if not uri.startswith(prefix):
        raise ArtifactUriUnresolvable(
            f"{uri!r} is not a {ARTIFACT_URI_SCHEME} URI"
        )
    body = uri[len(prefix) :]
    naming, separator, artifact_version = body.rpartition("@")
    if not separator:
        raise ArtifactUriUnresolvable(
            f"{uri!r} names no version; a versioned URI ends in @{{version}}"
        )
    if artifact_version == LATEST_VERSION_TOKEN:
        raise MovingTargetRefused(
            f"{uri!r} asks for @{LATEST_VERSION_TOKEN}; artifact resolution is "
            "exact-version only, because a record resolving a moving target "
            "does not describe the decision it was written for "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        )
    parts = naming.split("/")
    if len(parts) != 3 or not all(parts) or not artifact_version:
        raise ArtifactUriUnresolvable(
            f"{uri!r} is malformed; expected "
            f"{ARTIFACT_URI_SCHEME}://{{tenant}}/{{class}}/{{name}}@{{version}}"
        )
    tenant_id, artifact_class, name = parts
    return ArtifactName(
        tenant_id=tenant_id,
        artifact_class=artifact_class,
        name=name,
        artifact_version=artifact_version,
    )


class ArtifactRef(CCFContract):
    """A resolvable reference to one stored artifact version.

    Attributes:
        content_address: ``sha256`` of the artifact's canonical bytes. This is
            the identity; everything else on this contract is naming.
        uri: The versioned URI, carried as annotation (D-IMPL-26).
        tenant_id: Owning tenant — artifacts are tenant-scoped like everything
            else in the fabric (D-IMPL-05).
        artifact_class: Which class of artifact this is (replay record, policy
            bundle, agent definition, …). Deployment vocabulary; the SDK
            enumerates none of it.
        name: The logical name within the class.
    """

    content_address: str
    uri: str
    tenant_id: str
    artifact_class: str
    name: str


@runtime_checkable
class ArtifactStoreProtocol(Protocol):
    """Immutable, content-addressed artifact persistence (CLAUDE.md §7.4)."""

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Store ``artifact`` under the capability's tenant; return its reference.

        Idempotent by construction: storing byte-identical content again
        returns the same address and leaves the stored bytes untouched. There
        is deliberately no ``overwrite`` parameter.

        **This is the one write surface, and every transport reaches it.**
        An implementation's first statement is
        :func:`authorized_write_target`, which verifies ``authorized`` for the
        kind the store's :class:`WriteKinds` declaration names for the target
        class and resolves the tenant, class and name — from the capability's
        resource for an addressed write, from the :class:`DerivedWrite` for a
        derived one. Nothing about the target comes from a parameter
        (D-IMPL-353 §1.2, §1.3, §1.5f).

        Args:
            authorized: The capability for this write — ``ArtifactWrite`` for
                exactly ``"<class>/<name>"`` on the client lane; a declared
                mechanism kind for a declared class.
            artifact: The canonicalizable payload, or a :class:`DerivedWrite`
                wrapping one.

        Raises:
            ccf.authz.capability.CapabilityBypassError: fabricated,
                retargeted, or wrong-kind capability.
            ArtifactWriteRefused: the target shape.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form and therefore no stable identity.
        """
        ...

    def get(self, *, content_address: str) -> bytes:
        """Return the exact canonical bytes stored at ``content_address``.

        Bytes, not a parsed object: the store's contract is byte fidelity, and
        deciding which contract those bytes are is the caller's business.

        Raises:
            ArtifactNotFound: nothing is stored at that address.
        """
        ...

    def exists(self, *, content_address: str) -> bool:
        """Whether an artifact is stored at ``content_address``."""
        ...

    def resolve_uri(self, *, uri: str) -> str:
        """Return the content address a versioned URI names.

        Naming resolution, deliberately separate from :meth:`get`: identity is
        the content address and everything else is naming, so the two questions
        ("what is this named thing" and "what are its bytes") are two calls. A
        combined call would tempt an implementation to answer the first
        approximately.

        Registration is a side effect of :meth:`put` — there is no separate
        ``register_uri`` — so a name can never point at content the store does
        not hold.

        Raises:
            MovingTargetRefused: the URI asks for ``@latest``.
            ArtifactUriUnresolvable: the URI is malformed, or names a
                tenant/class/name/version combination this store never stored.
        """
        ...
