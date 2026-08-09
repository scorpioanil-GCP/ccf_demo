"""The Postgres graph write path — the D-IMPL-02 production backend.

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it.

**Import direction is one-way, and that is structural.** This module imports
its own reader module, :mod:`ccf.graph.backends.postgres`, freely. The reverse
is forbidden: if the reader imported the writer, every importer of the reader
would transitively reach write code and the CINV-02 rule would flag the reader
itself. The write module is therefore also where a ``REGISTRATION`` record
belongs (plan 15.4-04).

One algorithm, two dialects: this writer and its SQLite sibling share
:class:`~ccf.graph._writer.BaseGraphWriter` and
:class:`~ccf.graph._writer._SqlGraphTxn` unchanged. What differs is the
statement text — ``%s`` placeholders, ``LEAST``/``GREATEST`` for the observed
window, and ``seq`` where SQLite reads ``rowid``.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any, ClassVar

import psycopg
from pydantic import SecretStr

from ccf.contracts.base import CCFContract
from ccf.graph._writer import (
    BaseGraphWriter,
    BootToken,
    _GraphTxn,
    _SqlGraphTxn,
)
from ccf.graph.backends.postgres import DEFAULT_SCHEMA, PostgresGraphStore
from ccf.graph.reader import Row
from ccf.graph.registry import BackendRegistration, BackendStore

__ccf_mode__ = "algorithmic"

#: The name a manifest uses to select this adapter — the module's own stem less
#: ``_write``, which is how built-in discovery derives it.
ADAPTER_NAME = "postgres"

__all__ = ["REGISTRATION", "PostgresConnection", "PostgresGraphWriter"]


class _PostgresTxn:
    """``_Txn`` over a psycopg cursor inside an explicit transaction."""

    def __init__(self, cursor: psycopg.Cursor[dict[str, Any]]) -> None:
        self._cursor = cursor

    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        self._cursor.execute(sql.encode(), params)
        return max(self._cursor.rowcount, 0)

    def query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        self._cursor.execute(sql.encode(), params)
        return self._cursor.fetchall()


class PostgresGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Postgres graph — the D-IMPL-02 production backend.

    Same algorithm as :class:`SqliteGraphWriter`, inherited rather than
    restated. What differs is dialect: ``%s`` placeholders,
    ``LEAST``/``GREATEST`` for the observed-time window, and ``seq`` where
    SQLite reads ``rowid``.
    """

    UPSERT_ENTITY_NODE: ClassVar[str] = """
        INSERT INTO entities (
            tenant_id, entity_uri, entity_class, first_observed_at,
            last_observed_at
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET
            first_observed_at =
                LEAST(entities.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                GREATEST(entities.last_observed_at, excluded.last_observed_at)
    """
    INSERT_ENTITY_CLAIM: ClassVar[str] = """
        INSERT INTO entity_claims (
            tenant_id, entity_uri, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, entity_uri, claim_id) DO NOTHING
    """
    SELECT_ENTITY_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM entity_claims
        WHERE tenant_id = %s AND entity_uri = %s
        ORDER BY observed_at, seq
    """
    UPDATE_ENTITY_SUPERSESSION: ClassVar[str] = """
        UPDATE entity_claims SET superseded_by = %s, superseded_at = %s
        WHERE tenant_id = %s AND entity_uri = %s AND claim_id = %s
    """
    UPSERT_RELATIONSHIP_NODE: ClassVar[str] = """
        INSERT INTO relationships (
            tenant_id, relationship_key, relationship_type, subject_uri,
            object_uri, first_observed_at, last_observed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, relationship_key) DO UPDATE SET
            first_observed_at =
                LEAST(relationships.first_observed_at,
                      excluded.first_observed_at),
            last_observed_at =
                GREATEST(relationships.last_observed_at,
                         excluded.last_observed_at)
    """
    INSERT_RELATIONSHIP_CLAIM: ClassVar[str] = """
        INSERT INTO relationship_claims (
            tenant_id, relationship_key, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, relationship_key, claim_id) DO NOTHING
    """
    SELECT_RELATIONSHIP_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM relationship_claims
        WHERE tenant_id = %s AND relationship_key = %s
        ORDER BY observed_at, seq
    """
    UPDATE_RELATIONSHIP_SUPERSESSION: ClassVar[str] = """
        UPDATE relationship_claims SET superseded_by = %s, superseded_at = %s
        WHERE tenant_id = %s AND relationship_key = %s AND claim_id = %s
    """
    INSERT_LINEAGE: ClassVar[str] = """
        INSERT INTO lineage (
            tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        DO NOTHING
    """

    def __init__(self, *, store: PostgresGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        connection = self._store.connection
        with connection.transaction(), connection.cursor() as cursor:
            yield _SqlGraphTxn(txn=_PostgresTxn(cursor), statements=type(self))


class PostgresConnection(CCFContract):
    """The connection settings this adapter takes — and it takes no others.

    Plan 15.4-04, D-07. Derives from :class:`~ccf.contracts.base.CCFContract`
    so ``extra="forbid"`` is inherited: a settings key this adapter does not
    declare is refused rather than ignored, which is the refusal the old
    hand-maintained mapping in ``ccf.deployment.manifest`` performed with a loop
    over every other backend's argument.

    **No credential is a field here.** A DSN can carry a password, and Pydantic
    reports ``input_value=`` verbatim in a ``ValidationError`` — so this field is
    a *reference-bearing connection string supplied by the deployment*, exactly
    as ``postgres_dsn`` is today, and the same rule that keeps the Fluree token
    out of :class:`~ccf.graph.backends.fluree_write.FlureeConnection` applies to
    anything an adopter would otherwise be tempted to add here.

    Attributes:
        dsn: The libpq connection string. Required: a manifest declaring this
            adapter and omitting it is refused, and the fabric does not fall
            back to the development substrate.
        schema_name: Which schema in that database this fabric's graph lives in.
            Two schemas are two graphs, which is what makes the single-writer
            check meaningful per fabric rather than per database. Named
            ``schema_name`` rather than ``schema`` because a field named
            ``schema`` shadows an attribute on Pydantic's own ``BaseModel`` and
            emits a warning on every class construction; the store's keyword is
            unchanged and the mapping happens in :func:`_open_store`.
    """

    dsn: str
    schema_name: str = DEFAULT_SCHEMA


def _open_store(
    config: CCFContract, secrets: Mapping[str, SecretStr]
) -> BackendStore:
    """Construct this adapter's store from validated settings.

    Typed against the contract base so it is assignable to
    :attr:`~ccf.graph.registry.BackendRegistration.open_store` under
    ``mypy --strict``, then narrowed. ``secrets`` is unused: this adapter's
    credential travels inside the DSN, so it declares no secret field.
    """
    if not isinstance(config, PostgresConnection):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} takes a {PostgresConnection.__name__},"
            f" got a {type(config).__name__}"
        )
    return PostgresGraphStore(dsn=config.dsn, schema=config.schema_name)


def _make_writer(store: BackendStore, token: BootToken) -> BaseGraphWriter:
    """Construct the write handle — called by the composition root alone."""
    if not isinstance(store, PostgresGraphStore):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} writes through a"
            f" {PostgresGraphStore.__name__}, got a {type(store).__name__}"
        )
    return PostgresGraphWriter(store=store, token=token)


#: What this adapter declares about itself — the record
#: :func:`ccf.graph.registry.resolve` reads off this module.
REGISTRATION = BackendRegistration(
    name=ADAPTER_NAME,
    config_model=PostgresConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
