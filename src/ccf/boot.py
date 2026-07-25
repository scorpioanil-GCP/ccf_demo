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
    PostgresGraphWriter,
    SqliteGraphWriter,
    mint_boot_token,
)
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
) -> tuple[_Backend, Callable[[BootToken], BaseGraphWriter]]:
    """Select and open the graph backend named by explicit configuration.

    Selection is by explicit argument, never by inference from the shape of a
    string: a fabric that guessed its own substrate could silently boot against
    a development SQLite file in production and would still pass every test.
    SQLite remains the *default* (D-IMPL-02) precisely because it is the
    development backend; Postgres is chosen by saying so.

    Raises:
        ValueError: neither backend was named, or both were.
    """
    if (database_path is None) == (postgres_dsn is None):
        raise ValueError(
            "boot requires exactly one of database_path (SQLite) or "
            "postgres_dsn (Postgres); the fabric does not infer its substrate"
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
        database_path: SQLite file to attach to. Mutually exclusive with
            ``postgres_dsn``; exactly one must be given.
        postgres_dsn: libpq connection string for the Postgres backend. Comes
            from the deployment's environment; it is never persisted and never
            reproduced in the graph identity the single-writer check uses.
        postgres_schema: Postgres schema the fabric's tables live in. Two
            schemas on one database are two graphs.
        registry: Control Plane the resolution spec and policy bundle come from.
        resolution_spec_key: Key of the :class:`EntityResolutionSpec` artifact.
        resolution_spec_version: Pinned version of that artifact.
        policy_bundle_key: Key of the policy bundle in force.
        policy_bundle_version: Pinned version of that bundle.

    Raises:
        ValueError: neither or both of ``database_path`` / ``postgres_dsn``
            were given.
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
