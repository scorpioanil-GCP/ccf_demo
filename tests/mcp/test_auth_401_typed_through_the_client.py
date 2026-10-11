"""Repair 2.5 (a), as ruled: a 401 from the artifact server's guard reaches the MCP client as a TYPED authentication refusal.

Dave, 2026-10-09 10:54 MST (``D-IMPL-378``), verbatim: *"Return a typed authentication refusal for 401, preserving
its distinction from authorization denial and transport outage."* The finding (the "i" batch panel's
G-NAMES-GUARD-OUTAGE, findings brief §2.5): *"A 401 from the server's guard reaches ``names_at`` as
``McpServerUnreachable``, while SP §4.10 now says 'never as an outage'."* SEC-020 stays open: this module measures, it
closes nothing.

Measured on the base (``fe25536c``) with the shipped ``McpArtifactStore`` over streamable HTTP to the shipped artifact
server: when the server's guard answered HTTP 401 — no credential, a credential that is not a bearer token, or a
bearer token its verifier does not know — every read of the store (``names_at``, ``get``, ``exists``,
``resolve_uri``, ``match_subject``) raised ``ccf.mcp.errors.McpServerUnreachable``, an outage. The guard answers before
any identity exists, so the server decided nothing about the address asked: a 401 is neither an outage nor the
authorization refusal ``ccf.artifacts.protocol.ArtifactReadRefused``, which is an access decision about an address
for a credential the server authenticated, carrying the server's refusal shell. This module holds:

* each read raises the typed authentication refusal ``ccf.artifacts.protocol.ArtifactStoreUnauthenticated`` when the
  guard answers 401, chained from the guard's own HTTP 401 response (the mechanism, asserted by type and by status
  code, never by message);
* a 401, the server's refusal shell and a refused connection reach the caller as three types, none a subclass of
  another;
* control: the guard's other refusals — a credential without the required scope (HTTP 403) and the tenancy guard's
  denial — are not the authentication refusal; they still reach the client as ``McpServerUnreachable``, the stance
  SP §4.10 discloses;
* the typed access refusal carries the server's own cause, and the cause is not the same for every address: the
  measurement behind the narrowed docstrings of ``ArtifactReadRefused`` and ``McpArtifactStore.names_at`` (repair
  1.6; K18 (b), which predates the batch).

The transport is the deployment's: ``ccf.mcp.client.SyncMcpBridge``, ``ccf.mcp.client.run_with_session`` and the
streamable-HTTP client, against the built server's own ASGI app with its bearer middleware, in process (an
``httpx.ASGITransport`` stands where the socket would). The refused connection is a loopback port bound and released.
Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import pathlib
import socket
from collections.abc import Callable, Iterator, Mapping
from http import HTTPStatus
from typing import Any

import httpx
import pytest
from mcp.server.auth.settings import AuthSettings
from mcp.shared.exceptions import McpError
from pydantic import AnyHttpUrl

import ccf.artifacts.protocol as artifact_protocol
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import (
    ArtifactName,
    ArtifactNotFound,
    ArtifactReadRefused,
    ArtifactRef,
    ArtifactStoreError,
    WriteKinds,
    artifact_uri,
)
from ccf.authz.actions import ACTION_ARTIFACT_WRITE
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure.subject_match import SubjectMatchQuery
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpClientError, McpServerUnreachable
from ccf_runtime.mcp.artifact_server import build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.mcp import test_c2_tenant_hold_mcp as c2
from tests.mcp.guarded_servers import PRINCIPAL, SCOPE, TENANT, _entitlement_world, authorizer_granting

#: The base URL the in-process transport answers on. Nothing listens there; ``httpx.ASGITransport`` stands in.
BASE_URL = "http://127.0.0.1:8167"

#: The bearer the server's verifier knows, with the scope the server requires.
KNOWN_TOKEN = "auth-401-known-token"

#: A bearer the server's verifier knows, whose grant lacks the scope the server requires (the guard's 403).
SCOPELESS_TOKEN = "auth-401-scopeless-token"

#: The credential shapes the server's guard answers 401: what the store's HTTP client sends, as headers.
GUARD_401: Mapping[str, Mapping[str, str]] = {
    "a bearer token the verifier does not know": {"Authorization": "Bearer auth-401-no-such-token"},
    "no credential at all": {},
    "a credential that is not a bearer token": {"Authorization": "Basic YXV0aDQwMTpub3QtYS1iZWFyZXI="},
}

#: The headers of a credential the guard does not authenticate, for the tests whose subject is not the credential's shape.
UNKNOWN: Mapping[str, str] = GUARD_401["a bearer token the verifier does not know"]

#: An address nobody filed in any world here.
NOBODYS = hashlib.sha256(b"repair 2.5 (a): an address nobody filed").hexdigest()

#: A class no world here declares: the tenant's client lane.
CLIENT_CLASS = "fixture.auth-notes"

#: The bridge's deadline for every call here: generous, because an in-process server answers in milliseconds.
CALL_TIMEOUT_SECONDS = 60.0


# --- the world ---------------------------------------------------------------------------------------------------


class World:
    """One artifact substrate with one client-lane filing of ``TENANT``, and a builder for servers over it.

    A server's session manager runs once per server instance, so every connection builds its own server over the
    one substrate.
    """

    def __init__(self, tmp_path: pathlib.Path) -> None:
        self.tmp_path = tmp_path
        self.store = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=WriteKinds({}))
        self.own: ArtifactRef = self.store.put(
            capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/own"), {"note": "own"}
        )
        self._built = 0

    def server(self, *, deny_reads: bool = False) -> Any:
        """The shipped artifact server over the substrate; ``deny_reads`` narrows its authorizer to writes only."""
        self._built += 1
        source, recorder = _entitlement_world(self.tmp_path / f"entitlement-{self._built}")
        authorizer = (
            authorizer_granting(tenants=(TENANT,), actions=(ACTION_ARTIFACT_WRITE,))
            if deny_reads
            else authorizer_granting(tenants=(TENANT,))
        )
        return build_artifact_server(
            server_name="auth-401",
            store=self.store,
            token_verifier=SourceBackedTokenVerifier(
                source=StaticTokenSource(
                    grants={
                        KNOWN_TOKEN: TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT})),
                        SCOPELESS_TOKEN: TokenGrant(
                            client_id="principal-auth-401-scopeless", scopes=(), tenants=frozenset({TENANT})
                        ),
                    }
                )
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl("https://issuer.invalid"),
                resource_server_url=AnyHttpUrl(f"{BASE_URL}/mcp"),
                required_scopes=[SCOPE],
            ),
            authorizer=authorizer,
            entitlement_source=source,
            refusal_recorder=recorder,
            audit_log=ControlPlaneRegistry().audit_log,
            erasure_trust=declared_erasure_trust(),
            erasure_index=no_erasures(),
            control_plane=ControlPlaneRegistry(),
        )

    def own_uri(self) -> str:
        return artifact_uri(
            tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="own", artifact_version=self.own.content_address
        )


@contextlib.contextmanager
def store_over_http(
    server: Any, headers: Mapping[str, str], write_kinds: WriteKinds | None = None
) -> Iterator[McpArtifactStore]:
    """The shipped ``McpArtifactStore``, over streamable HTTP to ``server``'s own ASGI app, sending ``headers``.

    The names lane's harness (``tests/mcp/test_f1_names_refusal_typed_through_the_client.py``) with the credential
    as headers, so a test can send none, or one that is not a bearer token. The server's session manager runs once
    per server, inside its app's lifespan, and answers requests only on the loop that entered it; so the lifespan is
    entered by ONE task on the bridge's own loop and held open while the store is used, and every store call runs on
    that loop through ``SyncMcpBridge.run``, as a deployment's would.
    """
    app = server.streamable_http_app()
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:

        async def start() -> tuple[asyncio.Task[None], asyncio.Event]:
            stop = asyncio.Event()
            ready = asyncio.Event()

            async def serve() -> None:
                async with app.router.lifespan_context(app):
                    ready.set()
                    await stop.wait()

            loop = asyncio.get_running_loop()
            serving = loop.create_task(serve())
            waiting = loop.create_task(ready.wait())
            await asyncio.wait({serving, waiting}, return_when=asyncio.FIRST_COMPLETED)
            if serving.done():
                waiting.cancel()
                serving.result()
                raise AssertionError("the server's lifespan ended before it served anything")
            return serving, stop

        serving, stop = bridge.run(start())

        def http_client() -> httpx.AsyncClient:
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url=BASE_URL, headers=dict(headers)
            )

        try:
            yield McpArtifactStore(
                url=f"{BASE_URL}/mcp",
                bridge=bridge,
                write_kinds=WriteKinds({}) if write_kinds is None else write_kinds,
                http_client_factory=http_client,
            )
        finally:

            async def finish() -> None:
                stop.set()
                await serving

            bridge.run(finish())


@contextlib.contextmanager
def store_at_nothing(write_kinds: WriteKinds | None = None) -> Iterator[McpArtifactStore]:
    """The shipped store pointed at a loopback port bound and released: nothing answers there (a refused connection).

    ``write_kinds`` as :func:`store_over_http` takes it, for a caller composing a door that files records over the store.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield McpArtifactStore(
            url=f"http://127.0.0.1:{port}/mcp",
            bridge=bridge,
            write_kinds=WriteKinds({}) if write_kinds is None else write_kinds,
        )


# --- the mechanism, by type --------------------------------------------------------------------------------------


def authentication_refusal() -> type[BaseException]:
    """The ruled typed authentication refusal, or a MISSING CONTRACT failure that names it."""
    found = getattr(artifact_protocol, "ArtifactStoreUnauthenticated", None)
    if not (isinstance(found, type) and issubclass(found, BaseException)):
        pytest.fail(
            "MISSING CONTRACT: ccf.artifacts.protocol.ArtifactStoreUnauthenticated, the typed authentication refusal"
            " repair 2.5 (a) requires (D-IMPL-378, Dave, 2026-10-09 10:54 MST), does not exist on this tree"
        )
    return found


def raised_by(call: Callable[[], object], *, what: str) -> BaseException:
    """What ``call`` raised; a failure naming what it returned instead, if it returned."""
    try:
        returned = call()
    except Exception as raised:  # noqa: BLE001 - the raised type IS the observation
        return raised
    pytest.fail(f"{what}: returned {returned!r} where the server's guard refused the credential")


def assert_the_authentication_refusal(raised: BaseException, *, what: str) -> None:
    """The mechanism, by type: the typed authentication refusal, chained from the guard's own HTTP 401 response."""
    # The ruling's three-way distinction, each by type: not the outage, not the authorization refusal.
    assert not isinstance(raised, McpServerUnreachable), (
        f"{what}: the guard's 401 reached the client labeled an outage — {type(raised).__name__}: {str(raised)[:300]}"
    )
    assert not isinstance(raised, ArtifactReadRefused), (
        f"{what}: the guard's 401 reached the client as an access decision — {type(raised).__name__}"
    )
    refused = authentication_refusal()
    assert isinstance(raised, refused), f"{what}: {type(raised).__module__}.{type(raised).__name__}: {str(raised)[:300]}"
    # Neither a retry target nor an absence: no MCP-client error, and no ArtifactNotFound.
    assert not isinstance(raised, McpClientError), type(raised).__mro__
    assert not isinstance(raised, ArtifactNotFound), type(raised).__mro__
    assert isinstance(raised, ArtifactStoreError), type(raised).__mro__
    # The guard's own answer is the cause: an HTTP 401 response, read by its status code.
    cause = raised.__cause__
    assert isinstance(cause, httpx.HTTPStatusError), f"{what}: the refusal is chained from {cause!r}"
    assert cause.response.status_code == HTTPStatus.UNAUTHORIZED, cause.response.status_code


def single_cause(error: BaseException) -> BaseException | None:
    """The one failure an outage stands for: its cause, less any single-member exception groups around it."""
    cause = error.__cause__
    while isinstance(cause, BaseExceptionGroup) and len(cause.exceptions) == 1:
        cause = cause.exceptions[0]
    return cause


def a_subject_match_query() -> SubjectMatchQuery:
    return SubjectMatchQuery(
        tenant_id=TENANT,
        content_address=NOBODYS,
        subject_ref=hashlib.sha256(b"repair 2.5 (a): a subject").hexdigest(),
        key_paths=("customer.id",),
        subject_ref_salt="auth-401-salt",
    )


# --- R1: the probe, as a test ------------------------------------------------------------------------------------


@pytest.mark.parametrize("credential", list(GUARD_401))
def test_names_at_raises_the_typed_authentication_refusal_when_the_guard_answers_401(
    tmp_path: pathlib.Path, credential: str
) -> None:
    """The panel's probe (``p_d1_guard_refusal_names.py``) as a test, for each credential shape the guard answers 401.

    Positive control first: the same server, transport and store, presenting the token the verifier knows, are
    answered the names of the tenant's own filing — so the refusal below is the credential's, not the server's or
    the transport's."""
    world = World(tmp_path)
    with store_over_http(world.server(), {"Authorization": f"Bearer {KNOWN_TOKEN}"}) as known:
        assert known.names_at(content_address=world.own.content_address) == (
            ArtifactName(
                tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="own", artifact_version=world.own.content_address
            ),
        )
    with store_over_http(world.server(), GUARD_401[credential]) as refused:
        for what, address in (("the tenant's own filing", world.own.content_address), ("nobody's address", NOBODYS)):
            raised = raised_by(lambda a=address: refused.names_at(content_address=a), what=f"[{credential}] {what}")
            assert_the_authentication_refusal(raised, what=f"names_at at {what}, presenting {credential}")


# --- R2: every other read ----------------------------------------------------------------------------------------


READS: Mapping[str, Callable[[McpArtifactStore, World], object]] = {
    "get": lambda store, world: store.get(content_address=world.own.content_address),
    "exists": lambda store, world: store.exists(content_address=world.own.content_address),
    "resolve_uri": lambda store, world: store.resolve_uri(uri=world.own_uri()),
    "match_subject": lambda store, world: store.match_subject(
        query=a_subject_match_query(), door_signature="not-the-erasure-doors-signature"
    ),
}


@pytest.mark.parametrize("read", list(READS))
def test_every_other_read_raises_the_typed_authentication_refusal_when_the_guard_answers_401(
    tmp_path: pathlib.Path, read: str
) -> None:
    """``get``, ``exists``, ``resolve_uri`` and ``match_subject`` given a credential the guard answers 401.

    Positive control first, presenting the token the verifier knows: ``get`` answers the filing's bytes, ``exists``
    answers ``True``, ``resolve_uri`` answers its address, and ``match_subject`` reaches the tool, which declines a
    caller that is not the erasure door (``ArtifactStoreError``, exactly that type) — so each read below completes
    when the credential is authenticated."""
    world = World(tmp_path)
    with store_over_http(world.server(), {"Authorization": f"Bearer {KNOWN_TOKEN}"}) as known:
        if read == "match_subject":
            declined = raised_by(lambda: READS[read](known, world), what="match_subject, authenticated")
            assert type(declined) is ArtifactStoreError, type(declined).__mro__
        else:
            expected = {
                "get": canonical_bytes({"note": "own"}),
                "exists": True,
                "resolve_uri": world.own.content_address,
            }[read]
            assert READS[read](known, world) == expected, read
    with store_over_http(world.server(), UNKNOWN) as refused:
        raised = raised_by(lambda: READS[read](refused, world), what=read)
        assert_the_authentication_refusal(raised, what=f"{read}, presenting a token the verifier does not know")


# --- R3: three causes, three types -------------------------------------------------------------------------------


def test_a_401_an_access_refusal_and_an_outage_reach_the_caller_as_three_types(tmp_path: pathlib.Path) -> None:
    """The ruling's distinction, each case asserted by TYPE, at the same read (``names_at`` at nobody's address).

    * the guard's 401 (a token its verifier does not know): the typed authentication refusal;
    * the server's refusal shell (the token it knows, at an address the tenant never filed): ``ArtifactReadRefused``,
      the authorization refusal, carrying the shell;
    * a refused connection (nothing listening): ``McpServerUnreachable``, the outage.

    And at the class level: none of the three is a subclass of another, so ``except McpServerUnreachable`` (a retry)
    never catches the authentication refusal, and ``except ArtifactReadRefused`` (an access decision) never does."""
    unauthenticated = authentication_refusal()
    world = World(tmp_path)
    with store_over_http(world.server(), UNKNOWN) as store:
        guard_401 = raised_by(lambda: store.names_at(content_address=NOBODYS), what="the guard's 401")
    with store_over_http(world.server(), {"Authorization": f"Bearer {KNOWN_TOKEN}"}) as store:
        shell = raised_by(lambda: store.names_at(content_address=NOBODYS), what="the server's refusal shell")
    with store_at_nothing() as store:
        outage = raised_by(lambda: store.names_at(content_address=NOBODYS), what="a refused connection")

    assert_the_authentication_refusal(guard_401, what="the guard's 401")

    assert isinstance(shell, ArtifactReadRefused), f"{type(shell).__name__}: {str(shell)[:300]}"
    assert not isinstance(shell, unauthenticated), type(shell).__mro__
    assert not isinstance(shell, McpServerUnreachable), type(shell).__mro__

    assert isinstance(outage, McpServerUnreachable), f"{type(outage).__name__}: {str(outage)[:300]}"
    assert not isinstance(outage, unauthenticated), type(outage).__mro__
    assert not isinstance(outage, ArtifactReadRefused), type(outage).__mro__
    assert isinstance(single_cause(outage), httpx.ConnectError), repr(single_cause(outage))

    for one, other in (
        (unauthenticated, McpServerUnreachable),
        (unauthenticated, ArtifactReadRefused),
        (unauthenticated, ArtifactNotFound),
        (unauthenticated, McpClientError),
        (ArtifactReadRefused, unauthenticated),
        (McpServerUnreachable, unauthenticated),
    ):
        assert not issubclass(one, other), (one, other)
    assert issubclass(unauthenticated, ArtifactStoreError), unauthenticated.__mro__


# --- control: the guard's other refusals are not the authentication refusal --------------------------------------


GUARD_OTHER = ("a credential without the required scope (HTTP 403)", "the tenancy guard's denial")


@pytest.mark.parametrize("refusal", GUARD_OTHER)
def test_the_guards_other_refusals_are_not_the_authentication_refusal(tmp_path: pathlib.Path, refusal: str) -> None:
    """Control: only a 401 is the authentication refusal. A credential the verifier knows whose grant lacks the
    required scope is answered 403 by the guard; a credential the server's authorizer does not grant the read is
    refused by the tenancy guard, as a protocol error. Each row is checked to be what it says (the 403 response; the
    protocol error), and neither reaches the client as the authentication refusal. Both reach it as
    ``McpServerUnreachable``: the stance (K49) SP §4.10 discloses, measured here so the page and the code move
    together. Positive control for the denial row: the same token reads the tenant's own names where reads are
    granted."""
    world = World(tmp_path)
    found = getattr(artifact_protocol, "ArtifactStoreUnauthenticated", None)
    if refusal == GUARD_OTHER[0]:
        server, headers = world.server(), {"Authorization": f"Bearer {SCOPELESS_TOKEN}"}
    else:
        with store_over_http(world.server(), {"Authorization": f"Bearer {KNOWN_TOKEN}"}) as granted:
            assert granted.names_at(content_address=world.own.content_address)
        server, headers = world.server(deny_reads=True), {"Authorization": f"Bearer {KNOWN_TOKEN}"}
    with store_over_http(server, headers) as store:
        raised = raised_by(lambda: store.names_at(content_address=world.own.content_address), what=refusal)
    assert found is None or not isinstance(raised, found), (refusal, type(raised).__mro__)
    assert type(raised) is McpServerUnreachable, (refusal, type(raised).__mro__, str(raised)[:300])
    cause = single_cause(raised)
    if refusal == GUARD_OTHER[0]:
        assert isinstance(cause, httpx.HTTPStatusError), repr(cause)
        assert cause.response.status_code == HTTPStatus.FORBIDDEN, cause.response.status_code
    else:
        assert isinstance(cause, McpError), repr(cause)


# --- the measurement behind repair 1.6: the typed access refusal's cause is the server's -------------------------


def test_the_typed_access_refusal_carries_the_servers_own_cause_which_differs_by_address(
    tmp_path: pathlib.Path,
) -> None:
    """``ArtifactReadRefused`` carries the server's refusal shell whole, and the shell is not one answer for every
    address (K18 (b), which predates the batch). Through the shipped client, as the C-2 world's caller at ``full``:

    * a governed record of the caller's tenant determined for ANOTHER principal: cause ``unauthorized``, error code
      ``evidence-principal-mismatch``;
    * an address nobody filed: cause ``nonexistent``, error code ``evidence-absent``.

    So the typed refusal says the address cannot be verified through this credential; it does not always hide which
    case it is. This is what the narrowed docstrings of ``ArtifactReadRefused`` and ``McpArtifactStore.names_at``
    state."""
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_PRINCIPAL_MISMATCH

    world = c2._world(tmp_path / "c2")
    theirs = c2._file(world, c2._record(tenant=c2.TENANT, principal="principal-auth-401-other", subject="s-1"))
    causes: dict[str, tuple[str, str]] = {}
    with store_over_http(world.server, {"Authorization": "Bearer tok"}, world.store.write_kinds) as store:
        for what, address in (("another principal's record", theirs), ("nobody's address", NOBODYS)):
            raised = raised_by(lambda a=address: store.names_at(content_address=a), what=what)
            assert isinstance(raised, ArtifactReadRefused), f"{what}: {type(raised).__name__}: {str(raised)[:300]}"
            fields = raised.envelope.fields
            causes[what] = (str(fields.get("cause")), str(fields.get("error_code")))
    assert causes["another principal's record"] == (
        canonical_bytes("unauthorized").decode("utf-8"),
        canonical_bytes(ERROR_EVIDENCE_PRINCIPAL_MISMATCH).decode("utf-8"),
    ), causes
    assert causes["nobody's address"] == (
        canonical_bytes("nonexistent").decode("utf-8"),
        canonical_bytes(ERROR_EVIDENCE_ABSENT).decode("utf-8"),
    ), causes
