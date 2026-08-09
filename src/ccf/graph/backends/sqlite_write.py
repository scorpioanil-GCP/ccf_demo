"""The SQLite graph write path — the D-IMPL-02 development backend.

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it. A module that wanted a write handle would have
to name this import, and naming it fails CI.

**Import direction is one-way, and that is structural.** This module imports
its own reader module, :mod:`ccf.graph.backends.sqlite`, freely. The reverse is
forbidden: if the reader imported the writer, every importer of the reader
would transitively reach write code and the CINV-02 rule would flag the reader
itself. The write module is therefore also where a ``REGISTRATION`` record
belongs (plan 15.4-04), and it is the write module an entry point names.

The write *semantic* is not here. Content identity, lineage set-union, chain
restitching and tenant-scope refusal all live once in
:class:`~ccf.graph._writer.BaseGraphWriter`; this module contributes the
transaction handling and the dialect statements, and nothing else.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar

from pydantic import SecretStr

from ccf.contracts.base import CCFContract
from ccf.graph._writer import (
    BaseGraphWriter,
    BootToken,
    _GraphTxn,
    _SqlGraphTxn,
)
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.reader import Row
from ccf.graph.registry import BackendRegistration, BackendStore

__ccf_mode__ = "algorithmic"

#: The name a manifest uses to select this adapter. It is the module's own stem
#: less ``_write``, which is how built-in discovery derives it — and
#: :func:`ccf.graph.registry.resolve` refuses a record whose ``name`` disagrees
#: with the name it was resolved under, so the two cannot drift silently.
ADAPTER_NAME = "sqlite"

__all__ = ["REGISTRATION", "SqliteConnection", "SqliteGraphWriter"]


class _SqliteTxn:
    """``_Txn`` over a ``sqlite3`` connection inside a ``with connection`` block."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        cursor = self._connection.execute(sql, params)
        return max(cursor.rowcount, 0)

    def query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        return self._connection.execute(sql, params).fetchall()


class SqliteGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one SQLite graph — the D-IMPL-02 dev backend."""

    UPSERT_ENTITY_NODE: ClassVar[str] = """
        INSERT INTO entities (
            tenant_id, entity_uri, entity_class, first_observed_at,
            last_observed_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET
            first_observed_at =
                MIN(entities.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                MAX(entities.last_observed_at, excluded.last_observed_at)
    """
    INSERT_ENTITY_CLAIM: ClassVar[str] = """
        INSERT INTO entity_claims (
            tenant_id, entity_uri, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, entity_uri, claim_id) DO NOTHING
    """
    SELECT_ENTITY_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM entity_claims
        WHERE tenant_id = ? AND entity_uri = ?
        ORDER BY observed_at, rowid
    """
    UPDATE_ENTITY_SUPERSESSION: ClassVar[str] = """
        UPDATE entity_claims SET superseded_by = ?, superseded_at = ?
        WHERE tenant_id = ? AND entity_uri = ? AND claim_id = ?
    """
    UPSERT_RELATIONSHIP_NODE: ClassVar[str] = """
        INSERT INTO relationships (
            tenant_id, relationship_key, relationship_type, subject_uri,
            object_uri, first_observed_at, last_observed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, relationship_key) DO UPDATE SET
            first_observed_at =
                MIN(relationships.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                MAX(relationships.last_observed_at, excluded.last_observed_at)
    """
    INSERT_RELATIONSHIP_CLAIM: ClassVar[str] = """
        INSERT INTO relationship_claims (
            tenant_id, relationship_key, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, relationship_key, claim_id) DO NOTHING
    """
    SELECT_RELATIONSHIP_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM relationship_claims
        WHERE tenant_id = ? AND relationship_key = ?
        ORDER BY observed_at, rowid
    """
    UPDATE_RELATIONSHIP_SUPERSESSION: ClassVar[str] = """
        UPDATE relationship_claims SET superseded_by = ?, superseded_at = ?
        WHERE tenant_id = ? AND relationship_key = ? AND claim_id = ?
    """
    INSERT_LINEAGE: ClassVar[str] = """
        INSERT INTO lineage (
            tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        DO NOTHING
    """

    def __init__(self, *, store: SqliteGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        connection = self._store.connection
        with connection:
            yield _SqlGraphTxn(txn=_SqliteTxn(connection), statements=type(self))


class SqliteConnection(CCFContract):
    """The connection settings this adapter takes — and it takes no others.

    Plan 15.4-04, D-07. This is where the knowledge "which connection argument
    does this backend require" now lives: in the adapter, not in a
    hand-maintained mapping in ``ccf.deployment.manifest`` that had to be edited
    for every substrate.

    Deriving from :class:`~ccf.contracts.base.CCFContract` is load-bearing
    rather than stylistic. It supplies ``extra="forbid"``, and that inheritance
    is the *whole* of one of the two refusals this model replaces: a settings
    key this adapter does not declare is rejected rather than ignored. A model
    written against a plain open base would keep every valid manifest working
    and lose that refusal with nothing going red — which is why
    ``tests/deployment/test_adapter_config.py`` sweeps every registered adapter
    asserting it.

    Attributes:
        database_path: The SQLite file this fabric's graph lives in. Required —
            the second refusal, in its typed form: a manifest declaring this
            adapter and omitting the path is refused, and the fabric does not
            fall back. Annotated ``Path`` rather than ``str`` because Pydantic
            coerces a string to a ``Path`` and not the reverse, and callers pass
            both.
    """

    database_path: Path


def _open_store(
    config: CCFContract, secrets: Mapping[str, SecretStr]
) -> BackendStore:
    """Construct this adapter's store from validated settings.

    The parameter is typed as the contract base so this function is assignable
    to :attr:`~ccf.graph.registry.BackendRegistration.open_store` under
    ``mypy --strict``; the ``isinstance`` narrows it and says what arrived when
    it is not this adapter's model. ``secrets`` is unused: this adapter declares
    no credential, which is why its ``secret_fields`` is empty.
    """
    if not isinstance(config, SqliteConnection):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} takes a {SqliteConnection.__name__},"
            f" got a {type(config).__name__}"
        )
    return SqliteGraphStore(database_path=config.database_path)


def _make_writer(store: BackendStore, token: BootToken) -> BaseGraphWriter:
    """Construct the write handle — called by the composition root alone."""
    if not isinstance(store, SqliteGraphStore):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} writes through a"
            f" {SqliteGraphStore.__name__}, got a {type(store).__name__}"
        )
    return SqliteGraphWriter(store=store, token=token)


#: What this adapter declares about itself — the record
#: :func:`ccf.graph.registry.resolve` reads off this module.
REGISTRATION = BackendRegistration(
    name=ADAPTER_NAME,
    config_model=SqliteConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
