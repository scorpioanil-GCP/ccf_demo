"""The composition root — the one place a ``GraphWriter`` is constructed.

SDK-defined mechanism (CLAUDE.md §10; the whitepaper specifies the
single-writer *invariant*, not the wiring that realizes it). DESIGN.md §2A.5.3
names this module as layer 2 of the D-IMPL-41 stack: the composition root
constructs exactly one ``GraphWriter`` and injects it into L2 and nowhere else.

Everything the single-writer invariant rests on converges here, so it is worth
stating what each part is doing:

* :mod:`ccf.graph._writer` is imported by this module and by ``ccf.assembly``
  alone, enforced by the CINV-02 import lint. A module that wanted a write
  handle would have to name that import, and naming it fails CI.
* The token is minted once per graph and consumed by the one writer. A second
  boot against the same graph raises before any write can occur, rather than
  producing a second writer that quietly interleaves state the replay engine
  could never reconstruct.
* :class:`FabricHandle` exposes a reader, the worker, and the Control Plane.
  It has no writer attribute — not a private one either. Shutdown runs through
  a closure, so there is nothing on the handle to reach for.

**Honest residual claim, verbatim from DESIGN.md §9 (per the D-IMPL-41
ruling):** Python cannot make determined-insider evasion impossible. The claim
strength is *no unforced path exists, and every forced path fails CI or fails
at boot* — never a claim of absolute prevention. Every statement in this module
about single-writer enforcement carries exactly that strength and no more.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Protocol

from ccf.assembly.worker import (
    AssemblyWorker,
    EntityResolutionSpec,
    SpecDrivenEntityResolution,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph._writer import (
    BaseGraphWriter,
    BootToken,
    FlureeGraphWriter,
    MemoryGraphWriter,
    MongoGraphWriter,
    Neo4jGraphWriter,
    PostgresGraphWriter,
    SqliteGraphWriter,
    mint_boot_token,
)
from ccf.graph.backends.fluree import (
    DEFAULT_PARTITION as FLUREE_DEFAULT_PARTITION,
)
from ccf.graph.backends.fluree import FlureeGraphStore
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.postgres import DEFAULT_SCHEMA, PostgresGraphStore
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import GraphReader

__ccf_mode__ = "algorithmic"

__all__ = ["FabricHandle", "boot"]


class FabricHandle:
    """What a booted fabric hands back: read access, L2, and the Control Plane.

    Deliberately *not* a container for everything that was constructed. The
    write handle exists inside the worker and is unreachable from here, so
    "get the writer off the handle" is not a thing a caller can discover
    (DESIGN.md §2A.5.3 layer 2).
    """

    def __init__(
        self,
        *,
        reader: GraphReader,
        worker: AssemblyWorker,
        registry: ControlPlaneProtocol,
        shutdown: Callable[[], None],
    ) -> None:
        self.reader = reader
        self.worker = worker
        self.registry = registry
        self._shutdown = shutdown

    def close(self) -> None:
        """Retire the fabric: the writer stops accepting writes, the store closes.

        Releases the graph for a subsequent boot. This is orderly shutdown, not
        a way to hold two live writers — the retired writer refuses every
        further call.
        """
        self._shutdown()

    def __enter__(self) -> FabricHandle:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class _Backend(Protocol):
    """What ``boot`` needs of a graph backend, whichever substrate it is."""

    @property
    def graph_identity(self) -> str: ...

    @property
    def reader(self) -> GraphReader: ...

    def close(self) -> None: ...


def _open_backend(
    *,
    database_path: Path | str | None,
    postgres_dsn: str | None,
    postgres_schema: str,
    memory: bool,
    neo4j_uri: str | None,
    neo4j_partition: str | None,
    mongo_uri: str | None,
    mongo_partition: str | None,
    fluree_url: str | None,
    fluree_partition: str | None,
) -> tuple[_Backend, Callable[[BootToken], BaseGraphWriter]]:
    """Select and open the graph backend named by explicit configuration.

    Selection is by explicit argument, never by inference from the shape of a
    string: a fabric that guessed its own substrate could silently boot against
    a development SQLite file in production and would still pass every test.
    SQLite remains the *default* (D-IMPL-02) precisely because it is the
    development backend; Postgres is chosen by saying so — and so are the
    in-memory backend (Phase 15.2 D-06), the Neo4j backend (plan 15.2-12), the
    MongoDB backend (plan 15.2-13) and the Fluree backend (plan 15.3):
    ``memory=True``, ``neo4j_uri``, ``mongo_uri`` and ``fluree_url`` are
    explicit statements, never a fallback a missing connection argument
    degrades to.

    The Neo4j and MongoDB branches import their backends lazily: the ``neo4j``
    and ``pymongo`` drivers are optional extras, and boot stays importable —
    and every other branch stays bootable — in an environment without them.
    **The Fluree branch does not**, and the difference is the point: its wire
    client is ``httpx``, a core pin, so its import shape is the *Postgres*
    one — module-top, unconditional, no lazy deferral (SUBQ-14).

    Raises:
        ValueError: not exactly one backend was named.
    """
    selected = (
        (database_path is not None)
        + (postgres_dsn is not None)
        + memory
        + (neo4j_uri is not None)
        + (mongo_uri is not None)
        + (fluree_url is not None)
    )
    if selected != 1:
        raise ValueError(
            "boot requires exactly one of database_path (SQLite), "
            "postgres_dsn (Postgres), memory=True (in-memory), "
            "neo4j_uri (Neo4j), mongo_uri (MongoDB), or fluree_url "
            "(Fluree v4); the fabric does not infer its substrate"
        )
    if memory:
        memory_store = MemoryGraphStore()
        return memory_store, lambda token: MemoryGraphWriter(
            store=memory_store, token=token
        )
    if neo4j_uri is not None:
        # Lazy by design (the chroma_index precedent): the driver import
        # happens inside the store's constructor, and the module import here
        # is deferred so this branch is the first moment Neo4j is named.
        from ccf.graph.backends.neo4j import (  # noqa: PLC0415
            DEFAULT_PARTITION,
            Neo4jGraphStore,
        )

        neo4j_store = Neo4jGraphStore(
            uri=neo4j_uri,
            partition=(
                neo4j_partition
                if neo4j_partition is not None
                else DEFAULT_PARTITION
            ),
        )
        return neo4j_store, lambda token: Neo4jGraphWriter(
            store=neo4j_store, token=token
        )
    if mongo_uri is not None:
        # Lazy by design, same as the Neo4j branch above: the pymongo import
        # happens inside the store's constructor, and the module import here
        # is deferred so this branch is the first moment MongoDB is named.
        from ccf.graph.backends.mongo import (  # noqa: PLC0415
            DEFAULT_PARTITION as MONGO_DEFAULT_PARTITION,
        )
        from ccf.graph.backends.mongo import (  # noqa: PLC0415
            MongoGraphStore,
        )

        mongo_store = MongoGraphStore(
            uri=mongo_uri,
            partition=(
                mongo_partition
                if mongo_partition is not None
                else MONGO_DEFAULT_PARTITION
            ),
        )
        return mongo_store, lambda token: MongoGraphWriter(
            store=mongo_store, token=token
        )
    if fluree_url is not None:
        fluree_store = FlureeGraphStore(
            url=fluree_url,
            partition=(
                fluree_partition
                if fluree_partition is not None
                else FLUREE_DEFAULT_PARTITION
            ),
        )
        return fluree_store, lambda token: FlureeGraphWriter(
            store=fluree_store, token=token
        )
    if postgres_dsn is not None:
        pg_store = PostgresGraphStore(dsn=postgres_dsn, schema=postgres_schema)
        return pg_store, lambda token: PostgresGraphWriter(
            store=pg_store, token=token
        )
    assert database_path is not None  # narrowed by the exclusivity check above
    sqlite_store = SqliteGraphStore(database_path=database_path)
    return sqlite_store, lambda token: SqliteGraphWriter(
        store=sqlite_store, token=token
    )


def boot(
    *,
    database_path: Path | str | None = None,
    postgres_dsn: str | None = None,
    postgres_schema: str = DEFAULT_SCHEMA,
    memory: bool = False,
    neo4j_uri: str | None = None,
    neo4j_partition: str | None = None,
    mongo_uri: str | None = None,
    mongo_partition: str | None = None,
    fluree_url: str | None = None,
    fluree_partition: str | None = None,
    registry: ControlPlaneProtocol,
    resolution_spec_key: str,
    resolution_spec_version: str,
    policy_bundle_key: str,
    policy_bundle_version: str,
) -> FabricHandle:
    """Construct a fabric over one graph and return its handle.

    Every Control Plane binding is an explicit, pinned ``(key, version)`` pair.
    There are no defaults and no "latest": a fabric whose configuration could
    drift between boots is a fabric whose decisions cannot be replayed
    (D-IMPL-38, whitepaper §7.10).

    Args:
        database_path: SQLite file to attach to. Exactly one of this,
            ``postgres_dsn``, ``memory=True``, ``neo4j_uri``, ``mongo_uri``
            and ``fluree_url`` must be given.
        postgres_dsn: libpq connection string for the Postgres backend. Comes
            from the deployment's environment; it is never persisted and never
            reproduced in the graph identity the single-writer check uses.
        postgres_schema: Postgres schema the fabric's tables live in. Two
            schemas on one database are two graphs.
        memory: Boot against a fresh in-memory graph (Phase 15.2 D-06) — zero
            external dependencies, no connection argument, no persistence
            beyond the handle's life. Every ``memory=True`` boot is its own
            graph with its own synthetic identity: two memory fabrics are two
            fabrics, never a shared substrate.
        neo4j_uri: Bolt connection URI for the Neo4j backend (plan 15.2-12),
            optionally carrying userinfo. Requires the ``neo4j`` extra; the
            backend import is lazy, so boot stays importable without it. As
            with the Postgres DSN: comes from the deployment's environment,
            never persisted, and never reproduced in the graph identity.
        neo4j_partition: Which graph on the Neo4j server this fabric owns —
            the Postgres ``schema`` argument's role. ``None`` selects the
            adapter's default partition. Two partitions on one database are
            two graphs.
        mongo_uri: MongoDB connection URI for the MongoDB backend (plan
            15.2-13), optionally carrying userinfo. Requires the ``mongo``
            extra; the backend import is lazy, so boot stays importable
            without it. As with the Postgres DSN and the Bolt URI: comes from
            the deployment's environment, never persisted, and never
            reproduced in the graph identity.
        mongo_partition: Which graph in the MongoDB database this fabric owns
            — the ``neo4j_partition`` / Postgres ``schema`` role. ``None``
            selects the adapter's default partition.
        fluree_url: Server URL for the Fluree v4 backend (plan 15.3),
            optionally carrying userinfo. Requires **no extra** — the wire
            client is a core pin — so unlike the Neo4j and MongoDB branches
            this one imports at module top. As with every other connection
            argument: comes from the deployment's environment, never
            persisted, and never reproduced in the graph identity.
        fluree_partition: Which graph in the CCF-owned ledger this fabric owns
            — the ``mongo_partition`` / ``neo4j_partition`` / Postgres
            ``schema`` role. ``None`` selects the adapter's default partition.
        registry: Control Plane the resolution spec and policy bundle come from.
        resolution_spec_key: Key of the :class:`EntityResolutionSpec` artifact.
        resolution_spec_version: Pinned version of that artifact.
        policy_bundle_key: Key of the policy bundle in force.
        policy_bundle_version: Pinned version of that bundle.

    Raises:
        ValueError: not exactly one of ``database_path`` / ``postgres_dsn`` /
            ``memory=True`` / ``neo4j_uri`` / ``mongo_uri`` / ``fluree_url``
            was given.
        ccf.graph._writer.SingleWriterViolation: a live writer already exists
            for this graph.
        ccf.controlplane.registry.ControlPlaneMissing: a pinned key or version
            is not registered.
        TypeError: the resolution-spec artifact is not an
            :class:`EntityResolutionSpec`.
    """
    store, make_writer = _open_backend(
        database_path=database_path,
        postgres_dsn=postgres_dsn,
        postgres_schema=postgres_schema,
        memory=memory,
        neo4j_uri=neo4j_uri,
        neo4j_partition=neo4j_partition,
        mongo_uri=mongo_uri,
        mongo_partition=mongo_partition,
        fluree_url=fluree_url,
        fluree_partition=fluree_partition,
    )
    try:
        token = mint_boot_token(graph_identity=store.graph_identity)
    except BaseException:
        store.close()
        raise

    writer = make_writer(token)

    def shutdown() -> None:
        writer.close()
        store.close()

    try:
        spec = registry.resolve(resolution_spec_key, resolution_spec_version)
        if not isinstance(spec, EntityResolutionSpec):
            raise TypeError(
                f"artifact at ({resolution_spec_key!r}, "
                f"{resolution_spec_version!r}) is "
                f"{type(spec).__name__}, not EntityResolutionSpec"
            )
        worker = AssemblyWorker(
            writer=writer,
            resolution=SpecDrivenEntityResolution(spec=spec),
            registry=registry,
            policy_bundle_key=policy_bundle_key,
            policy_bundle_version=policy_bundle_version,
        )
    except BaseException:
        # A half-booted fabric must not leave the graph marked as written-to;
        # otherwise a corrected retry would be refused as a second writer.
        shutdown()
        raise

    return FabricHandle(
        reader=store.reader,
        worker=worker,
        registry=registry,
        shutdown=shutdown,
    )
