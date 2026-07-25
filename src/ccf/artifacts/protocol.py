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

__all__ = ["ARTIFACT_URI_SCHEME", "ArtifactRef", "ArtifactStoreProtocol", "artifact_uri"]

ARTIFACT_URI_SCHEME = "ccf-artifact"


def artifact_uri(
    *, tenant_id: str, artifact_class: str, name: str, artifact_version: str
) -> str:
    """Render the D-IMPL-26 versioned URI for one artifact version."""
    return (
        f"{ARTIFACT_URI_SCHEME}://{tenant_id}/{artifact_class}/"
        f"{name}@{artifact_version}"
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
            KeyError: nothing is stored at that address.
        """
        ...

    def exists(self, *, content_address: str) -> bool:
        """Whether an artifact is stored at ``content_address``."""
        ...
