"""MCP-backed ArtifactStore — the §7.4 reference implementation.

SDK-defined (CLAUDE.md §7.4: users "are free to use their own persistent store
and decision-playback data store by standing up (or pointing at) an MCP server
that implements the artifact resource contract"); addressing per D-IMPL-26.
The server half is :mod:`ccf_runtime.mcp.artifact_server`.

This class is the file-backed store's peer, not its successor: it presents the
same four synchronous :class:`~ccf.artifacts.protocol.ArtifactStoreProtocol`
methods and passes the same conformance suite, so swapping one for the other is
a change of constructor and nothing else.

**It reuses the shared bridge; it does not build one.** The async→sync seam
lives in :mod:`ccf.mcp.client` because ``Agent.invoke_skill`` needs the same
one. A second bridge here would fork the deadlock risk across two modules, and
the deadlock in question is real: a held ``ClientSession`` entered from a
blocking portal never returns (06-RESEARCH.md B3, verified at a 120 s timeout).
No loop is created here and no work is scheduled onto one here — the two names
that would do either are absent from this file by assertion, because writing
them would be rebuilding what is already imported.

**It reuses the shared URI grammar; it does not re-derive it.**
:func:`~ccf.artifacts.protocol.parse_artifact_uri` is what a URI *means*, for
every store. Routing through it is why this store refuses ``@latest`` with the
same typed error the file store does, without a line here that mentions the
moving target.

**Absence and outage are discriminated on a structured answer, never a
message.** ``McpError``'s text is a stringified server-side exception with no
typed code, so matching it would bind this store's absent/unreachable
distinction to another project's error formatting — a server that reworded
itself would silently start reporting missing artifacts as outages
(06-RESEARCH.md Pitfall 2, T-06-21). A failed blob read is therefore *not*
taken as absence: the store asks the presence resource, which answers
``found: false`` on a successful read, and only that answer becomes
:class:`~ccf.artifacts.protocol.ArtifactNotFound`. Everything else stays
:class:`~ccf.mcp.errors.McpServerUnreachable` — over-reporting absence is the
dangerous direction, because absence is what a replay writes down as a fact
about the past. There is no ``except McpError`` handler in this file.

**A write requires the capability for its own action, here AND at the
server (D-IMPL-353 §1.2).** :func:`~ccf.artifacts.protocol.authorized_write_target`
runs before the payload is even encoded, so a fabricated, retargeted or
wrong-kind capability never reaches the wire and the refusal is this store's
own; the store the artifact server holds runs the identical check over the
capability the server's wrapper minted for the remote caller — so a remote
client that skips this class entirely and speaks to the server directly meets
the same rule. That is the property that makes the rule the store's rather
than any transport's. What crosses the wire is the resolved target (tenant,
class, name) and the bytes; the capability itself never does — the server
mints its own for the caller it authenticated.

**The naming index is the server's.** This store holds none. Two stores
pointed at one server therefore resolve identically, which is what makes a URI
recorded years ago resolvable by a process that never wrote it — and it is why
nothing here caches an address.

**What this cannot do.** It reads and writes artifacts and nothing else. It
holds no graph handle of any kind and imports nothing from L3; an artifact
retrieved through here enters the Context Graph only by going through L2 like
any other claim, so the single-writer invariant (CLAUDE.md §10) is untouched by
this store's existence.

The server URL, the credentials, and the call deadline are all deployment
values supplied by the caller. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import base64
import json
from collections.abc import Coroutine
from typing import Any, TypeVar

from mcp import ClientSession
from mcp.types import BlobResourceContents, TextResourceContents
from pydantic import AnyUrl

from ccf.artifacts.protocol import (
    ArtifactNotFound,
    ArtifactRef,
    ArtifactStoreError,
    ArtifactUriUnresolvable,
    ArtifactWriteAuthority,
    MalformedContentAddress,
    WriteKinds,
    artifact_uri,
    authorized_write_target,
    held_content_address,
    parse_artifact_uri,
)
from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.client import (
    HttpClientFactory,
    SessionOperation,
    SyncMcpBridge,
    run_with_session,
)
from ccf.mcp.errors import McpServerUnreachable

_T = TypeVar("_T")

__ccf_mode__ = "algorithmic"

__all__ = ["McpArtifactStore"]

#: Kept in step with :mod:`ccf_runtime.mcp.artifact_server` by the invariant
#: test that reads both modules; declared here rather than imported because
#: ``/src`` does not depend on ``/runtime`` (D-04), and a client that could not
#: talk to a third party's server would not be a Protocol implementation.
_BLOB_SCHEME = "ccf-artifact-blob"
_META_SCHEME = "ccf-artifact-meta"
_PUT_TOOL = "put_artifact"


class McpArtifactStore:
    """Content-addressed artifacts held by an MCP artifact server (§7.4).

    Args:
        url: The server's streamable-HTTP endpoint. A deployment value.
        bridge: The shared sync↔async bridge from :mod:`ccf.mcp.client`.
            Injected rather than constructed here: it owns a background thread,
            and an object that manufactured one internally would hide that
            thread's lifetime from the caller who has to close it.
        http_client_factory: Builds the HTTP client each call runs on — where
            the bearer token for an authenticated server goes (D-26). Optional
            only because the seam has to admit an unauthenticated development
            server; a deployment that omits it against an authenticated one
            gets :class:`~ccf.mcp.errors.McpServerUnreachable`, not silent
            anonymous access.
        write_kinds: The deployment's declaration of which artifact classes
            are mechanism-written and under which kinds (D-IMPL-353 §1.2).
            **Required, no default.** Enforced *before the call leaves this
            process*, exactly as ``@latest`` is, so the refusal is this
            store's own and a server outage cannot turn it into something
            else. The server behind the URL runs the identical check over its
            own store's declaration.
    """

    def __init__(
        self,
        *,
        url: str,
        bridge: SyncMcpBridge,
        write_kinds: WriteKinds,
        http_client_factory: HttpClientFactory | None = None,
    ) -> None:
        self._url = url
        self._bridge = bridge
        self._http_client_factory = http_client_factory
        self._write_kinds = write_kinds

    @property
    def url(self) -> str:
        """The server this store reads and writes through."""
        return self._url

    @property
    def write_kinds(self) -> WriteKinds:
        """Which artifact classes are mechanism-written here, and by which kinds."""
        return self._write_kinds

    # --- transport ---------------------------------------------------------

    def _session(
        self, operation: SessionOperation[_T]
    ) -> Coroutine[Any, Any, _T]:
        """One session-per-call coroutine, credentials attached."""
        return run_with_session(
            url=self._url,
            operation=operation,
            http_client_factory=self._http_client_factory,
        )

    def _read_blob(self, uri: str) -> bytes:
        """Read one resource as bytes, concatenated in server order.

        ``BlobResourceContents`` carries base64 and is what a ``-> bytes``
        server handler produces. Text parts are ignored rather than decoded:
        mixing them in would silently reintroduce the text round trip this
        whole path exists to avoid (Pitfall 4).
        """

        async def operation(session: ClientSession) -> bytes:
            result = await session.read_resource(AnyUrl(uri))
            return b"".join(
                base64.b64decode(contents.blob)
                for contents in result.contents
                if isinstance(contents, BlobResourceContents)
            )

        return self._bridge.run(self._session(operation))

    def _read_text(self, uri: str) -> str:
        """Read one resource as text, concatenated in server order."""

        async def operation(session: ClientSession) -> str:
            result = await session.read_resource(AnyUrl(uri))
            return "".join(
                contents.text
                for contents in result.contents
                if isinstance(contents, TextResourceContents)
            )

        return self._bridge.run(self._session(operation))

    # --- the four Protocol methods -----------------------------------------

    def put(self, authorized: ArtifactWriteAuthority, artifact: object) -> ArtifactRef:
        """Store ``artifact`` under the capability's tenant and return its reference.

        :func:`~ccf.artifacts.protocol.authorized_write_target` runs before the
        payload is even encoded, so a refused write never reaches the wire and
        the refusal is typed rather than whatever a remote server happened to
        answer. The canonical bytes are computed here, by the same serializer
        the content address is defined over, and carried as base64; the server
        re-derives them from what it parses and refuses the write if the two
        disagree, so neither side has to trust the other's serializer.

        Raises:
            ccf.authz.capability.CapabilityBypassError: the capability is
                fabricated, retargeted, or not of a kind that writes the
                target class. Raised before the call leaves this process.
            ccf.artifacts.protocol.ArtifactWriteRefused: the target shape.
            ccf.contracts.canonical.CanonicalizationError: the artifact has no
                canonical form and therefore no stable identity. Raised before
                anything reaches the wire.
            ccf.mcp.errors.McpServerUnreachable: the substrate is unreachable
                or refused the credentials.
            ArtifactStoreError: the server declined the write.
        """
        target, payload_artifact = authorized_write_target(
            authorized, artifact, write_kinds=self._write_kinds
        )
        payload = base64.b64encode(canonical_bytes(payload_artifact)).decode("ascii")

        async def operation(session: ClientSession) -> ArtifactRef:
            result = await session.call_tool(
                _PUT_TOOL,
                {
                    "tenant_id": target.tenant_id,
                    "artifact_class": target.artifact_class,
                    "name": target.name,
                    "canonical_b64": payload,
                },
            )
            if result.isError or result.structuredContent is None:
                raise ArtifactStoreError(
                    f"the artifact server declined to store {target.name!r}"
                )
            return ArtifactRef.model_validate(result.structuredContent)

        return self._bridge.run(self._session(operation))

    def get(self, *, content_address: str) -> bytes:
        """Return the exact canonical bytes stored at ``content_address``.

        Raises:
            ArtifactNotFound: the server answered, on the presence resource,
                that it holds nothing at that address. Only that structured
                answer produces this error.
            ccf.mcp.errors.McpServerUnreachable: the read failed and the server
                did not say the artifact was absent — so it is an outage, which
                invites a retry, rather than an absence, which gets written
                down.
        """
        try:
            return self._read_blob(
                f"{_BLOB_SCHEME}://{held_content_address(content_address)}"
            )
        except McpServerUnreachable:
            # The failed read tells us nothing typed; the presence resource
            # does. Asking costs a round trip only on the failure path, which
            # is the right place to spend it.
            if not self.exists(content_address=content_address):
                raise ArtifactNotFound(content_address) from None
            raise

    def exists(self, *, content_address: str) -> bool:
        """Whether an artifact is stored at ``content_address``.

        A successful read either way — ``found: false`` is an answer, not a
        failure. That is what makes this the discriminator :meth:`get` leans on.

        Raises:
            ccf.mcp.errors.McpServerUnreachable: the substrate is unreachable
                or refused the credentials.
        """
        try:
            addressed = held_content_address(content_address)
        except MalformedContentAddress:
            # Not an address, so nothing is stored at it — and no round trip
            # is spent asking a server about a string it could not hold
            # (`D-IMPL-345` `S-02`).
            return False
        answer = self._read_text(f"{_META_SCHEME}://{addressed}")
        return _presence_of(answer)

    def resolve_uri(self, *, uri: str) -> str:
        """Return the content address ``uri`` names, exactly.

        Raises:
            ccf.artifacts.protocol.MovingTargetRefused: the URI asks for the
                moving target. Raised by the shared parser before the call
                leaves this process, so every store refuses it identically and
                a server outage cannot turn the refusal into something else.
            ArtifactUriUnresolvable: the URI is malformed, or the server
                answered that it registered no such version under that name.
            ccf.mcp.errors.McpServerUnreachable: the substrate is unreachable.
        """
        parsed = parse_artifact_uri(uri)
        # Re-rendered through the shared renderer rather than forwarding the
        # caller's string: the parser is what a URI means, and a store that
        # passed the raw text on would let a malformed-but-prefixed URI reach
        # the server as though the grammar had accepted it.
        answer = self._read_text(
            artifact_uri(
                tenant_id=parsed.tenant_id,
                artifact_class=parsed.artifact_class,
                name=parsed.name,
                artifact_version=parsed.artifact_version,
            )
        )
        address = _resolution_of(answer)
        if address is None:
            raise ArtifactUriUnresolvable(
                f"{uri!r} names no version the artifact server registered"
            )
        return address


def _presence_of(answer: str) -> bool:
    """Read the ``found`` flag out of a presence answer.

    Parsed structurally, with a hard failure when the shape is wrong: a
    malformed answer coerced to ``False`` would be this module reporting an
    absence it was never told about.

    Raises:
        McpServerUnreachable: the answer is not the presence contract, which
            means the thing on the other end is not an artifact server.
    """
    try:
        parsed = json.loads(answer)
        found = parsed["found"]
    except (ValueError, KeyError, TypeError) as error:
        raise McpServerUnreachable(
            f"artifact server returned a non-presence answer: {answer!r}"
        ) from error
    if not isinstance(found, bool):
        raise McpServerUnreachable(
            f"artifact server returned a non-boolean presence: {answer!r}"
        )
    return found


def _resolution_of(answer: str) -> str | None:
    """Read the resolved address, or ``None``, out of a resolution answer.

    Raises:
        McpServerUnreachable: the answer is not the resolution contract.
    """
    try:
        parsed = json.loads(answer)
        found = parsed["found"]
        address = parsed["content_address"]
    except (ValueError, KeyError, TypeError) as error:
        raise McpServerUnreachable(
            f"artifact server returned a non-resolution answer: {answer!r}"
        ) from error
    if not found:
        return None
    if not isinstance(address, str):
        raise McpServerUnreachable(
            f"artifact server resolved to a non-address: {answer!r}"
        )
    return address
