"""The erasure mechanism's typed refusals (SEC-009; `D-IMPL-374` (4)).

A module of their own so the index and the decorating store can both raise
them without importing each other.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from ccf.artifacts.protocol import ArtifactStoreError

__ccf_mode__ = "algorithmic"

__all__ = [
    "INDEX_CORRUPT",
    "ErasedContentRefused",
    "ErasureCompositionRefused",
    "ErasureIndexCorrupt",
    "ErasureIndexInsecure",
]

#: The reason every read carries while the index is corrupt (fix round 2, N3).
INDEX_CORRUPT: Final[str] = "index-corrupt"


class ErasedContentRefused(ArtifactStoreError):
    """The address holds content a recorded erasure says is not served (SEC-009; `D-IMPL-374` (4)).

    Raised by :class:`~ccf.erasure.ErasureConsultingStore` on a read of an
    erased address, in place of the bytes. An
    :class:`~ccf.artifacts.protocol.ArtifactStoreError` and deliberately **not**
    an ``ArtifactNotFound`` nor a ``LookupError``: an erasure is a recorded
    decision, not an absence (G5).

    Carries the erasure's record address, reason and instant **only** for a
    read scoped to the erasing tenant and an entry its record supports — the
    facts are the RECORD's (fix round 2, N2); a tenantless read, an
    unsupported entry and a corrupt index carry ``None`` there (I6; §8; N3).
    Never anything of the subject. The bytes it withholds remain on the
    substrate; no destruction is claimed.

    **Its text names no address at all** — neither the erased content address
    nor the record address (M8; FW-3, whole-branch review I-2, ``D-IMPL-374``).
    The addresses are structured attributes for an in-process caller. The text
    is what a transport that renders exception prose would put on a wire, and
    the whole-branch review measured exactly that: this text, naming the erased
    address, reached a ``minimal`` principal through the MCP doors. Every SDK
    door now maps the class by disclosure level instead
    (``ccf_runtime.authz.delivery_boundary.govern_erasure``), and the text stays
    address-free for any door that does not.
    """

    def __init__(
        self,
        *,
        content_address: str,
        erasure_record_address: str | None,
        reason: str | None,
        erased_at: datetime | None,
    ) -> None:
        super().__init__(
            "the requested content was erased by a recorded decision and is not served (SEC-009)"
        )
        self.content_address = content_address
        self.erasure_record_address = erasure_record_address
        self.reason = reason
        self.erased_at = erased_at


class ErasureIndexCorrupt(ErasedContentRefused):
    """The erasure index cannot be read as an unbroken chain of entries — FAIL CLOSED (SEC-009; `D-IMPL-374` (4), N3).

    Raised by the index for a line that does not parse or whose recorded
    predecessor hash breaks the chain, and by the decorating store for EVERY
    read under that index until it is repaired: an index that cannot say what
    is erased withholds everything rather than serving anything. An
    :class:`ErasedContentRefused` (reason ``index-corrupt``, no facts), so
    every door that maps an erasure maps this one — never a 500.
    """

    def __init__(self, detail: str, *, content_address: str = "") -> None:
        ArtifactStoreError.__init__(self, f"the erasure index is corrupt: {detail} (SEC-009; N3)")
        self.content_address = content_address
        self.erasure_record_address = None
        self.reason = INDEX_CORRUPT
        self.erased_at = None


class ErasureIndexInsecure(PermissionError):
    """The erasure index file is not private to this process's user (SEC-009; `D-IMPL-374` (4), fix round 2 (a)).

    Refused at open, by name: a symlink, a file not owned by the effective
    user or not mode ``0600``, or a parent directory not owned by it or open
    beyond ``0700``. Anyone who can write the index can append a forged entry
    or truncate its tail.
    """


class ErasureCompositionRefused(TypeError):
    """A store construction site composed the erasure consult without its trust root, or over a different one (SEC-009; `D-IMPL-374` (4), fix round 4, ruling 5).

    Raised at composition — where an operator sees it — never at a read, by
    name: the site passed no Control Plane (there is no fresh-registry
    fallback; a consult verifying against a registry that lacks the
    deployment's policies would mark every genuine erasure
    ``index-unsupported``), or no HITL policy key, or it re-composed a store
    already composed with a DIFFERENT Control Plane, identity provider or HITL
    policy key — which would otherwise be silently ignored, leaving the store
    verifying against a trust root the site did not name.
    """
