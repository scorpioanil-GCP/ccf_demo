"""SEC-013 (D-IMPL-374 (1)): a network-store writer refuses to mint without a declared, held lease.

Whitepaper §7.3 and INV-CH7-10 (exactly one writer per graph); CLAUDE.md §10
("the single-writer invariant ... is architectural, not advisory"). The hole as
worded: "``_LIVE_WRITERS`` is process-local" — before D-IMPL-374 the three
persistent network stores declared ``"process"`` lease scope only, so a second
*process* booting the same network graph minted a second writer.

The ruling (a): a persistent network store mints a writer only under a
deployment-declared lease that is HELD (a ``"cross-process"`` lease — the
reference lock-file lease or the reference advisory-lock lease, reused against
the network graph), and a network store with no declared lease REFUSES to mint,
by name (``WriterLeaseRequired``).

**No socket opens and no server is touched.** Each store's network client is
replaced by an in-process double before construction (an ``httpx``
``MockTransport``; a fake ``MongoClient``; a fake Bolt driver), in the parent
and again inside every spawned child. The advisory-lock lease is exercised
against a recorded-protocol double of a Postgres session, never a server.
Lock files live in ``tmp_path``.
"""

from __future__ import annotations

import contextlib
import functools
import multiprocessing as mp
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

_TIMEOUT_SECONDS = 120

NETWORK_SUBSTRATES = ("fluree", "mongo", "neo4j")

#: The connection-contract field a deployment declares the lock-file lease by.
LEASE_FIELD = "writer_lease_lock_file"


# --- Network-client doubles ---------------------------------------------------


class _FakeMongoCollection:
    def create_index(self, *_args: Any, **_kwargs: Any) -> str:
        return "ix"


class _FakeMongoDatabase:
    def __getitem__(self, _name: str) -> _FakeMongoCollection:
        return _FakeMongoCollection()


class _FakeMongoAdmin:
    def command(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": 1}


class _FakeMongoClient:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.admin = _FakeMongoAdmin()

    def __getitem__(self, _name: str) -> _FakeMongoDatabase:
        return _FakeMongoDatabase()

    def close(self) -> None:
        return None


class _FakeNeo4jResult:
    def consume(self) -> None:
        return None


class _FakeNeo4jSession:
    def __enter__(self) -> _FakeNeo4jSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def run(self, *_args: Any, **_kwargs: Any) -> _FakeNeo4jResult:
        return _FakeNeo4jResult()


class _FakeNeo4jDriver:
    def verify_connectivity(self) -> None:
        return None

    def session(self, **_kwargs: Any) -> _FakeNeo4jSession:
        return _FakeNeo4jSession()

    def close(self) -> None:
        return None


class _FakeGraphDatabase:
    @staticmethod
    def driver(*_args: Any, **_kwargs: Any) -> _FakeNeo4jDriver:
        return _FakeNeo4jDriver()


@contextlib.contextmanager
def _offline_clients() -> Iterator[None]:
    """Replace all three network clients with in-process doubles, then restore."""
    import httpx
    import neo4j
    import pymongo

    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/fluree.json":
            return httpx.Response(200, json={"api_base_url": "/v1/fluree"})
        if request.url.path.endswith("/create"):
            return httpx.Response(409, json={})
        return httpx.Response(200, json={})

    def _client(**kwargs: Any) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    saved = (httpx.Client, pymongo.MongoClient, neo4j.GraphDatabase)
    httpx.Client = _client  # type: ignore[misc,assignment]
    pymongo.MongoClient = _FakeMongoClient  # type: ignore[misc,assignment]
    neo4j.GraphDatabase = _FakeGraphDatabase  # type: ignore[misc,assignment]
    try:
        yield
    finally:
        httpx.Client, pymongo.MongoClient, neo4j.GraphDatabase = saved  # type: ignore[misc]


def _connection(substrate: str, partition: str) -> dict[str, Any]:
    """A server-free connection mapping; the host never resolves."""
    if substrate == "fluree":
        return {"url": "http://graph.invalid:8090", "partition": partition}
    if substrate == "mongo":
        return {"uri": "mongodb://graph.invalid:27017/ccf", "partition": partition}
    if substrate == "neo4j":
        return {"uri": "neo4j://graph.invalid:7687", "partition": partition}
    raise NotImplementedError(substrate)


def _boot(backend: str, connection: dict[str, Any]) -> "FabricHandle":
    """Boot one fabric through the real composition root, the suite's recipe."""
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    from tests.composition import register_at_composition
    from tests.conftest import (
        FIXTURE_TENANTS,
        POLICY_BUNDLE_KEY,
        RESOLUTION_SPEC_KEY,
        _policy_bundle,
        _resolution_spec,
    )

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(
        registry, RESOLUTION_SPEC_KEY, _resolution_spec()
    )
    policy_version = register_at_composition(
        registry, POLICY_BUNDLE_KEY, _policy_bundle()
    )
    return boot(
        backend=backend,
        connection=connection,
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=FIXTURE_TENANTS,
    )


def _child_boot(
    backend: str,
    connection: dict[str, Any],
    queue: "mp.Queue[tuple[str, str, str, str]]",
) -> None:
    """Spawned child — a second PROCESS: install the doubles, attempt one boot."""
    with _offline_clients():
        try:
            handle = _boot(backend, connection)
        except BaseException as exc:  # reported by name, asserted by the parent
            cause = exc.__cause__
            queue.put(
                (
                    "REFUSED",
                    type(exc).__name__,
                    "" if cause is None else type(cause).__name__,
                    str(exc),
                )
            )
            return
        queue.put(("BOOTED", "", "", ""))
        handle.close()


def _run_child(
    backend: str, connection: dict[str, Any]
) -> tuple[str, str, str, str]:
    ctx = mp.get_context("spawn")
    queue: mp.Queue[tuple[str, str, str, str]] = ctx.Queue()
    process = ctx.Process(target=_child_boot, args=(backend, connection, queue))
    process.start()
    try:
        outcome = queue.get(timeout=_TIMEOUT_SECONDS)
    finally:
        process.join(timeout=_TIMEOUT_SECONDS)
    return outcome


# --- (a) two processes, one network graph, one shared declared lease ----------


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_second_process_cannot_mint_a_writer_for_a_held_network_graph(
    substrate: str, tmp_path: Path
) -> None:
    """Process A holds the network graph under a declared lease; process B is refused.

    The hole as worded: ``_LIVE_WRITERS`` is process-local, so before
    D-IMPL-374 a second process minted a writer over the same network graph.
    With a shared lease declared, the second process's mint is refused —
    ``SingleWriterViolation`` caused by the substrate lease's ``WriterLeaseHeld``.
    After the holder closes, the lease is given back with its boot token and a
    fresh process boots.
    """
    connection = _connection(substrate, f"lease_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(tmp_path / f"{substrate}-writer.lock")
    with _offline_clients():
        holder = _boot(substrate, connection)
        try:
            status, exc_name, cause_name, message = _run_child(substrate, connection)
        finally:
            holder.close()

    assert (status, exc_name, cause_name) == (
        "REFUSED",
        "SingleWriterViolation",
        "WriterLeaseHeld",
    ), (
        f"a second process obtained a writer over a {substrate} graph another"
        f" process holds: child reported {status!r} {exc_name!r}"
        f" {cause_name!r} {message!r}"
    )
    assert "already exists" in message

    status, exc_name, cause_name, message = _run_child(substrate, connection)
    assert status == "BOOTED", (
        f"the holder released the graph but a second process was refused:"
        f" {exc_name!r} {cause_name!r} {message!r}"
    )


# --- (b) a network store with no declared lease refuses to mint ---------------


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_network_store_with_no_declared_lease_refuses_to_mint(
    substrate: str,
) -> None:
    """No declared lease → the mint refuses by name; nothing is left marked live.

    Before D-IMPL-374 this boot minted a writer under a ``"process"``-scope
    declaration that excludes nothing across processes.
    """
    connection = _connection(substrate, f"unleased_{uuid.uuid4().hex}")
    with _offline_clients():
        try:
            handle = _boot(substrate, connection)
        except BaseException as exc:
            refused: BaseException | None = exc
        else:
            handle.close()
            refused = None

    assert refused is not None, (
        f"a {substrate} store with no declared writer lease minted a writer"
    )
    assert type(refused).__name__ == "WriterLeaseRequired", repr(refused)
    message = str(refused)
    assert "SEC-013" in message
    assert "D-IMPL-374" in message


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_refused_unleased_mint_leaves_the_graph_bootable(
    substrate: str, tmp_path: Path
) -> None:
    """The refusal marks nothing live: a corrected, leased boot then succeeds."""
    connection = _connection(substrate, f"retry_{uuid.uuid4().hex}")
    with _offline_clients():
        with pytest.raises(Exception) as refused:
            _boot(substrate, connection)
        assert type(refused.value).__name__ == "WriterLeaseRequired"
        connection[LEASE_FIELD] = str(tmp_path / "retry.lock")
        _boot(substrate, connection).close()


# --- The declared lease, the token, and the advisory-lock reuse ----------------


def _store(substrate: str, partition: str, writer_lease: Any) -> Any:
    from ccf.graph.backends.fluree import FlureeGraphStore
    from ccf.graph.backends.mongo import MongoGraphStore
    from ccf.graph.backends.neo4j import Neo4jGraphStore

    location = _connection(substrate, partition)
    if substrate == "fluree":
        return FlureeGraphStore(
            url=location["url"], partition=partition, writer_lease=writer_lease
        )
    if substrate == "mongo":
        return MongoGraphStore(
            uri=location["uri"], partition=partition, writer_lease=writer_lease
        )
    return Neo4jGraphStore(
        uri=location["uri"], partition=partition, writer_lease=writer_lease
    )


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_the_boot_token_records_the_held_leases_scope_and_identity(
    substrate: str, tmp_path: Path
) -> None:
    """SEC-013-C-03: the token says which lease it was minted under, not only its scope."""
    from ccf.graph._writer import mint_boot_token, release_boot_token
    from ccf.graph.backends.sqlite import SqliteWriterLease

    sidecar = tmp_path / "token.lock"
    with _offline_clients():
        store = _store(
            substrate,
            f"token_{uuid.uuid4().hex}",
            functools.partial(SqliteWriterLease, sidecar=sidecar),
        )
        try:
            token = mint_boot_token(store=store)
            try:
                assert token.lease_scope == "cross-process"
                assert token.lease_mechanism == f"flock on {str(sidecar)!r}"
            finally:
                release_boot_token(token)
        finally:
            store.close()


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_a_declared_process_scoped_lease_is_not_a_held_lease(
    substrate: str,
) -> None:
    """Declaring the ``"process"`` disclosure is declaring no lease: refused by name."""
    from ccf.graph._writer import mint_boot_token
    from ccf.graph.protocols import ProcessScopedWriterLease

    with _offline_clients():
        store = _store(
            substrate,
            f"declared_{uuid.uuid4().hex}",
            functools.partial(ProcessScopedWriterLease, substrate="declared"),
        )
        try:
            with pytest.raises(Exception) as refused:
                mint_boot_token(store=store)
        finally:
            store.close()
    assert type(refused.value).__name__ == "WriterLeaseRequired"


class _AdvisoryLockServer:
    """A recorded-protocol double of one Postgres server's advisory-lock table."""

    def __init__(self) -> None:
        self.holders: dict[str, int] = {}


class _AdvisoryResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class _AdvisorySession:
    """One session against :class:`_AdvisoryLockServer`, search_path = ``schema``."""

    def __init__(self, server: _AdvisoryLockServer, schema: str) -> None:
        self._server = server
        self._schema = schema
        self.closed = False

    def execute(self, statement: str) -> _AdvisoryResult:
        holder = self._server.holders.get(self._schema)
        if "pg_try_advisory_lock" in statement:
            held = holder is None or holder == id(self)
            if held:
                self._server.holders[self._schema] = id(self)
            return _AdvisoryResult({"schema_name": self._schema, "held": held})
        if "pg_advisory_unlock" in statement:
            released = holder == id(self)
            if released:
                del self._server.holders[self._schema]
            return _AdvisoryResult({"released": released})
        raise AssertionError(f"unexpected statement {statement!r}")


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_the_advisory_lock_lease_is_reusable_against_a_network_graph(
    substrate: str,
) -> None:
    """The reference advisory-lock lease keys a network graph through a lease schema.

    Two stores over one network graph, each declaring the advisory lease on its
    own session to one (double) server under one lease schema: the second
    acquisition is refused with ``WriterLeaseHeld``, and released it is granted.
    """
    from ccf.graph.backends.postgres import PostgresWriterLease
    from ccf.graph.protocols import WriterLeaseHeld

    server = _AdvisoryLockServer()
    lease_schema = f"ccf_lease_{uuid.uuid4().hex}"
    partition = f"advisory_{uuid.uuid4().hex}"

    def declared() -> Any:
        return functools.partial(
            PostgresWriterLease,
            connection=_AdvisorySession(server, lease_schema),
            schema=lease_schema,
        )

    with _offline_clients():
        first = _store(substrate, partition, declared())
        second = _store(substrate, partition, declared())
        try:
            held = first.writer_lease()
            assert held.scope == "cross-process"
            with pytest.raises(WriterLeaseHeld):
                second.writer_lease()
            held.release()
            second.writer_lease().release()
        finally:
            first.close()
            second.close()
