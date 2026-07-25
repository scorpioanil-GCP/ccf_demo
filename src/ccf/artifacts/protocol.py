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

from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARTIFACT_URI_SCHEME",
    "LATEST_VERSION_TOKEN",
    "ArtifactName",
    "ArtifactNotFound",
    "ArtifactRef",
    "ArtifactStoreError",
    "ArtifactStoreProtocol",
    "ArtifactUriUnresolvable",
    "MovingTargetRefused",
    "artifact_uri",
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
        self, *, tenant_id: str, artifact_class: str, name: str, artifact: object
    ) -> ArtifactRef:
        """Store ``artifact`` and return its reference.

        Idempotent by construction: storing byte-identical content again
        returns the same address and leaves the stored bytes untouched. There
        is deliberately no ``overwrite`` parameter.

        Raises:
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
