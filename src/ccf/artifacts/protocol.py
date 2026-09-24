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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from typing import Final, Protocol, runtime_checkable

from pydantic import model_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARTIFACT_URI_SCHEME",
    "CONTENT_ADDRESS_PATTERN",
    "LATEST_VERSION_TOKEN",
    "NAME_SEGMENT_SEPARATOR",
    "NOTHING_GOVERNED",
    "ArtifactName",
    "ArtifactNotFound",
    "ArtifactRef",
    "ArtifactStoreError",
    "ArtifactStoreProtocol",
    "ArtifactUriUnresolvable",
    "GovernedClassDeclarationError",
    "GovernedRecordClasses",
    "GovernedWriteForgery",
    "GovernedWriteHandle",
    "GovernedWriteRefused",
    "GovernedWriteToken",
    "MalformedContentAddress",
    "MovingTargetRefused",
    "artifact_uri",
    "held_content_address",
    "held_writable_class",
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


class GovernedWriteRefused(ArtifactStoreError):
    """A write named an artifact class only fabric mechanism may file under.

    ``SEC-004``. The store's write path took four values — tenant, class, name,
    payload — and every one of them arrives off the wire at the HTTP artifact
    door (``ArtifactPutRequest``) and at the MCP ``put_artifact`` tool. A client
    therefore chose the artifact class its bytes were filed under, *including*
    the class a deployment keeps its Decision Replay records in, and the plant
    was then resolvable through that class's naming lane. Content addressing
    does not close it: an address proves INTEGRITY — these bytes hash to this
    address — and never PROVENANCE, so a replay resolving the forged URI would
    reproduce the plant and validate it as genuine.

    **Not an** :class:`ArtifactNotFound`. A refused write is a determination the
    fabric made, not an absence; typing it as absence would tell a caller its
    write had vanished rather than been refused, and would be swallowed by every
    ``except ArtifactNotFound`` written for the read path. **Not an**
    ``OSError`` either: that is the substrate's family, and this refusal is
    raised before the substrate is reached, so a caller distinguishing "the disk
    failed" from "you may not write here" keeps the distinction.

    **What it discloses.** Exactly one bit, about the caller's own supplied
    string: *the class you named is governed here*. It names no other member of
    the declaration, and it does not vary with what the store already holds —
    the refusal is decided before canonicalization, before addressing and before
    any substrate contact, so it cannot become the write-path twin of the
    existence oracle :class:`MalformedContentAddress` closes on the read path
    (``D-IMPL-253`` amendment 2 (4)).
    """


class GovernedWriteForgery(GovernedWriteRefused):
    """Something was presented as minting authority that this module did not mint.

    **A subclass of** :class:`GovernedWriteRefused`, deliberately: to the caller
    it is the same refusal — the write does not happen — and a door that catches
    the parent catches this identically. The separate type exists for the
    deployment that is debugging its own wiring, exactly as
    :class:`MalformedContentAddress` is separable from ordinary absence.

    It is the reason the mint check is *identity against a module-private
    sentinel* rather than a truthiness test. A door that forwarded a JSON body
    field would present ``True``, ``1``, ``"minted"`` or ``{"_minted": true}``,
    and every one of those passes ``if minted:``. None of them is
    :data:`_GOVERNED_WRITE_TOKEN`.
    """


class GovernedClassDeclarationError(ArtifactStoreError):
    """A deployment declared an artifact class that cannot be governed.

    Raised at declaration — at boot, where an operator sees it — rather than at
    request time, because an unusable declaration is a misconfiguration and not
    a decision about any caller.

    Deliberately **not** a ``ValueError`` even though it reports a malformed
    value: it is raised from a Pydantic ``model_validator``, and Pydantic
    absorbs ``ValueError`` into its own ``ValidationError``. A typed refusal
    that the validation framework rewrote into an untyped one would leave
    callers matching on message text.
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


class GovernedRecordClasses(CCFContract):
    """Which artifact classes only fabric mechanism may file under (``SEC-004``).

    **The SDK cannot name them, so the deployment declares them.** There is no
    SDK constant for "the replay record class": :mod:`ccf.replay.serve` takes it
    as a constructor argument and says so in as many words — *"Deployment
    vocabulary, so it is supplied rather than assumed"* — and the same is true
    of query pins, HITL actions, admission records and everything else an
    adopter files. A set of class names baked into ``/src`` would be precisely
    the hard-coded domain vocabulary CLAUDE.md §6.4 forbids, and it would be
    wrong for every deployment that spells its classes differently.

    So the shape is the one this project uses everywhere a value is the
    adopter's and the rule is the SDK's: **the deployment declares, mechanism
    enforces.** The declaration is a value bound to the store at construction —
    deployment-side, boot-time, never per request — which is where CLAUDE.md §10
    already puts the single-writer invariant (*"enforce via dependency injection
    at boot"*). Nothing a caller sends can widen it, narrow it, or restate it:
    a request body supplies the class being classified, never the set it is
    classified against.

    **Membership is exact.** No casefolding and no trimming. Normalizing would
    make two genuinely distinct naming lanes compare equal, which is a worse
    defect than the near-miss it would catch — and a near-miss gains a caller
    nothing, because its bytes register under a key no genuine URI resolves.

    Attributes:
        class_ids: The declared classes. A ``frozenset`` because this is
            genuinely a membership question and has no order to preserve; the
            canonical serializer sorts it, so two deployments that declared the
            same classes in different order record the same bytes.

    Raises:
        GovernedClassDeclarationError: a declared id is empty, is not its own
            ``strip()``, or contains :data:`NAME_SEGMENT_SEPARATOR`.
    """

    class_ids: frozenset[str]

    @classmethod
    def declare(cls, *class_ids: str) -> GovernedRecordClasses:
        """Declare the governed classes by name.

        The documented constructor. ``GovernedRecordClasses.declare("x", "y")``
        reads as the deployment statement it is, where
        ``GovernedRecordClasses(class_ids=frozenset({...}))`` reads as plumbing.
        """
        return cls(class_ids=frozenset(class_ids))

    @model_validator(mode="after")
    def _every_id_is_governable(self) -> GovernedRecordClasses:
        """Refuse a declaration mechanism could not actually enforce.

        The separator rule is measured, not stylistic. A file-backed naming key
        is ``f"{tenant}{sep}{artifact_class}{sep}{name}"``, so a key built from a
        slash-free class id contains exactly two separators and has exactly one
        ``(tenant, class, name)`` decomposition — the one naming the governed
        class, which is refused. Let the class id carry a separator and that
        stops being true: ``class="a/b", name="x"`` and ``class="a", name="b/x"``
        produce the identical key ``t/a/b/x``, and only the first is refused. The
        declaration would then describe a lane with a documented bypass, so it is
        refused at boot instead. :func:`parse_artifact_uri` agrees independently
        — it splits the naming half into exactly three segments, so such a class
        could never round-trip through a versioned URI either.

        The empty and untrimmed rules catch the other way a declaration fails
        silently: an id that does not match the string the fabric actually writes
        governs nothing at all, and does so without complaint.
        """
        for class_id in sorted(self.class_ids):
            if not class_id or class_id != class_id.strip():
                raise GovernedClassDeclarationError(
                    f"{class_id!r} is not a usable artifact class id; a governed"
                    " class must be a non-empty string with no surrounding"
                    " whitespace, because an id that does not match the string"
                    " the fabric writes governs nothing and says nothing"
                )
            if NAME_SEGMENT_SEPARATOR in class_id:
                raise GovernedClassDeclarationError(
                    f"{class_id!r} contains {NAME_SEGMENT_SEPARATOR!r}, so a"
                    " client could reach its naming lane by splitting the id"
                    " across `artifact_class` and `name`; declare a class id"
                    " that is one naming segment (SEC-004)"
                )
        return self

    def governs(self, artifact_class: str) -> bool:
        """Whether ``artifact_class`` is one only mechanism may write."""
        return artifact_class in self.class_ids


#: The explicit empty declaration, and the stores' default.
#:
#: Named rather than left as ``frozenset()`` so a store that governs nothing
#: *says* so — ``store.governed is NOTHING_GOVERNED`` is answerable — instead of
#: leaving the question unasked. A deployment holding this is in the posture it
#: was in before ``SEC-004`` was closed, which is why the declaration is the one
#: thing an adopter must now add.
NOTHING_GOVERNED: Final[GovernedRecordClasses] = GovernedRecordClasses(
    class_ids=frozenset()
)

#: The sentinel a genuine minting authority carries. Module-private and
#: compared by identity, never by truthiness: a door that forwarded a request
#: body field would present ``True``, ``1``, ``"minted"`` or
#: ``{"_minted": true}``, and every one of those satisfies ``if minted:``.
_GOVERNED_WRITE_TOKEN = object()


class GovernedWriteToken:
    """Evidence that a write is the fabric's own and not a client's (``SEC-004``).

    Not constructible outside this module: the constructor demands the
    module-private sentinel, and :func:`held_writable_class` verifies the mint
    rather than trusting the type — so a subclass that skips this ``__init__``
    is refused at the write. This is
    :class:`ccf.controlplane.state.StateWriteToken`'s posture, for the same
    reason and with the same honesty about its limit.

    The only supported producer is :class:`GovernedWriteHandle`.

    **Scope, stated rather than overclaimed.** What this makes unrepresentable
    is a *wire-originated* governed write: no JSON body, no MCP tool argument
    and no query string can produce a Python object, so no remote caller can
    mint. Python has no barrier that stops a door's *author* from importing the
    handle; that is covered by CI (``tests/artifacts`` asserts no module under
    ``runtime/ccf_runtime`` names either symbol), never claimed impossible.
    """

    __slots__ = ("_minted",)

    def __init__(self, token: object) -> None:
        if token is not _GOVERNED_WRITE_TOKEN:
            raise GovernedWriteForgery(
                "GovernedWriteToken is minted only by"
                " ccf.artifacts.protocol.GovernedWriteHandle; a governed record"
                " class is written by fabric mechanism holding that handle, and"
                " by nothing a transport hands through (SEC-004)"
            )
        self._minted = _GOVERNED_WRITE_TOKEN


def held_writable_class(
    artifact_class: str,
    *,
    governed: GovernedRecordClasses,
    minted: GovernedWriteToken | None,
) -> str:
    """Return ``artifact_class`` if this writer may file under it (``SEC-004``).

    The ONE governance check every store's write path runs **before it
    canonicalizes the artifact, derives an address, or touches its substrate**.
    Placed on the Protocol module rather than in a door for the reason
    :func:`held_content_address` is: the doors are not where the substrate is
    touched. HTTP ``POST /artifact``, the MCP ``put_artifact`` tool, the CLI and
    every in-process caller all reach a store's ``put``, so a check at one door
    leaves the others filing records. Authorizing the HTTP route instead would
    also convert unauthorized forgery into *authorized* forgery — any principal
    holding artifact-write could still mint a replay record — which is why the
    refusal is here and not there.

    **Order is load-bearing.** A presented authority is verified first, so a
    mis-wired door that forwards a caller's value is refused on every class
    rather than only on governed ones, and the operator sees it immediately.
    Only then is the declaration consulted, and that consultation depends on
    nothing but the caller's own string and the deployment's boot-time
    declaration — never on what the store already holds. That is what keeps the
    refusal from becoming an existence oracle.

    Args:
        artifact_class: The class a writer asked to file under.
        governed: The deployment's declaration, bound to the store at
            construction. Never a per-call value.
        minted: The fabric's authority, or ``None`` for an ordinary write.
            ``None`` can only make this stricter; there is no value of this
            argument that skips the check.

    Returns:
        The class, unchanged, so a call site reads as a pass-through.

    Raises:
        GovernedWriteForgery: something was presented as authority that this
            module did not mint.
        GovernedWriteRefused: the class is governed and no authority was
            presented.
    """
    if minted is not None and (
        getattr(minted, "_minted", None) is not _GOVERNED_WRITE_TOKEN
    ):
        raise GovernedWriteForgery(
            "the value presented as minting authority was not minted by"
            " ccf.artifacts.protocol.GovernedWriteHandle (SEC-004)"
        )
    if minted is None and governed.governs(artifact_class):
        raise GovernedWriteRefused(
            f"{artifact_class!r} is a governed record class on this store and is"
            " written by fabric mechanism only; a client cannot file bytes under"
            " it, because an address proves integrity and never provenance"
            " (SEC-004; CLAUDE.md §7.4)"
        )
    return artifact_class


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

    def put(
        self,
        *,
        tenant_id: str,
        artifact_class: str,
        name: str,
        artifact: object,
        minted: GovernedWriteToken | None = None,
    ) -> ArtifactRef:
        """Store ``artifact`` and return its reference.

        Idempotent by construction: storing byte-identical content again
        returns the same address and leaves the stored bytes untouched. There
        is deliberately no ``overwrite`` parameter.

        **This is the client-facing write surface**, and it is the one every
        transport reaches. An implementation runs
        :func:`held_writable_class` over ``artifact_class`` before it
        canonicalizes anything, so an artifact class the deployment declared
        governed is refused here (``SEC-004``).

        Args:
            tenant_id: Owning tenant.
            artifact_class: The class to file under. A *declaration* to be
                checked, never the authority to write.
            name: The logical name within the class.
            artifact: The canonicalizable payload.
            minted: The fabric's own authority for a governed record class,
                obtained from :class:`GovernedWriteHandle` and from nowhere
                else. ``None`` — the default, and the only value any transport
                can produce — means an ordinary client write. Passing it can
                only require *more* authority, never less: there is no value of
                this argument that skips the check.

        Raises:
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form and therefore no stable identity.
            GovernedWriteRefused: ``artifact_class`` is governed and no
                authority was presented.
            GovernedWriteForgery: something that is not a minted authority was
                presented as one.
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


class GovernedWriteHandle:
    """The fabric's write handle for governed record classes (``SEC-004``).

    SDK-defined; CLAUDE.md §7.4 (the ArtifactStore seam) and §10 (*"enforce via
    dependency injection at boot"*).

    **This is how the fabric's own writer still writes a governed record**, and
    it required no change to any writer. An
    :class:`~ccf.replay.serve.ReplayWriter` takes an
    :class:`ArtifactStoreProtocol`; this handle *is* one, delegating every
    method to the store it wraps and attaching the minted authority to the one
    call that needs it. A deployment injects the handle where it injects the
    store today::

        store = FileArtifactStore(root=..., governed=declaration)   # doors
        fabric = GovernedWriteHandle(store)                         # mechanism
        ReplayWriter(store=fabric, artifact_class=declaration_class)

    The asymmetry is the whole point, and it is the single-writer invariant's
    shape applied to the artifact substrate: **a transport door is handed the
    store, mechanism is handed the handle, and nothing in a request body turns
    one into the other.**

    The handle grants no read authority it did not already have — the three
    read methods are plain delegation — because reads are governed at the
    delivery boundary (``D-IMPL-345``), not here.

    Args:
        store: The substrate this handle mints against. Any conforming
            implementation; the handle adds authority, never behavior.
    """

    def __init__(self, store: ArtifactStoreProtocol) -> None:
        self._store = store
        self._token = GovernedWriteToken(_GOVERNED_WRITE_TOKEN)

    @property
    def store(self) -> ArtifactStoreProtocol:
        """The substrate behind this handle."""
        return self._store

    def put(
        self,
        *,
        tenant_id: str,
        artifact_class: str,
        name: str,
        artifact: object,
        minted: GovernedWriteToken | None = None,
    ) -> ArtifactRef:
        """Store ``artifact`` with this handle's authority attached.

        ``minted`` is accepted so the handle satisfies
        :class:`ArtifactStoreProtocol` exactly, and is ignored: the handle's own
        authority is the one that travels. A caller that supplied a forged token
        here would gain nothing and lose nothing — the write was already
        authorized by holding the handle.
        """
        return self._store.put(
            tenant_id=tenant_id,
            artifact_class=artifact_class,
            name=name,
            artifact=artifact,
            minted=self._token,
        )

    def get(self, *, content_address: str) -> bytes:
        return self._store.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        return self._store.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        return self._store.resolve_uri(uri=uri)
