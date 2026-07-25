"""``SqliteVecIndex`` — the D-IMPL-03 reference vector substrate (dev default).

Whitepaper §7.4 (Similarity as a canonical operator category with a pinned
corpus version, INV-CH7-27); CLAUDE.md §12 D-IMPL-03 (a ``SimilarityIndex``
Protocol with pluggable reference implementations) and §11 ("Reference
implementations ship alongside Protocols"). This is the local-first one — the
same posture SQLite holds for the graph store (D-IMPL-02): no server, no
vendor account, and a deployment can run the whole fabric from a file.

Built on sqlite-vec 0.1.9's ``vec0`` virtual table, loaded as a SQLite
extension. Three shape decisions are worth stating because they are not the
obvious ones:

* **``tenant_id`` is a vec0 partition key, not a filtered column.** Partitioning
  makes the tenant part of the physical layout, so a query that forgot to scope
  cannot accidentally range over a neighbour's vectors — the isolation is in the
  storage, not in a ``WHERE`` clause anyone could drop (T-04-25).
* **``entity_uri`` is an auxiliary column rather than the table's primary key.**
  vec0 enforces primary-key uniqueness *globally*, across partitions, so a URI
  used by two tenants would collide — which is precisely the cross-tenant
  coupling the partition key exists to prevent. Uniqueness per ``(tenant_id,
  entity_uri)`` is maintained by :meth:`upsert` deleting before it inserts.
* **Ranking is an exact scan over the supplied candidates, not a KNN query.**
  ``MATCH ... k = n`` searches the whole partition and returns its own top-n;
  intersecting that with the candidate set afterwards would silently drop
  admissible candidates that lost to inadmissible ones. Policy runs before
  Similarity (INV-CH7-26), so the candidate set is *already* the answer's
  universe, and scoring exactly it is both correct and cheaper.

Not tagged ``__ccf_mode__ = "algorithmic"``: this module invokes an
:class:`~ccf.similarity.embedder.EmbedderProtocol`, and an embedding model is a
semantic stage. The tag would assert something untrue about the code path, and
CINV-03 is worth more as a claim than as a decoration.
"""

from __future__ import annotations

import sqlite3

# sqlite-vec 0.1.9 ships no py.typed marker. The ignore is scoped to this one
# import rather than declared as a project-wide mypy override because the
# untyped surface is genuinely one module wide: three calls (`load`,
# `serialize_float32`) and one SQL function, each of whose results is coerced
# to a declared type before it leaves this file.
import sqlite_vec  # type: ignore[import-untyped]

from ccf.similarity.embedder import EmbedderProtocol
from ccf.similarity.protocol import (
    SimilarityHit,
    cosine_score_percent,
    order_hits,
)

__all__ = ["SqliteVecIndex"]

#: Table name for the vector store. A schema identifier, not a domain value —
#: the No-Hardcoding Rule (CLAUDE.md §6.4) is about prompts, thresholds, and
#: ontologies, and a deployment that needs a different name overrides it.
DEFAULT_TABLE = "ccf_similarity_vectors"

#: SQLite's default bound-parameter ceiling is well above this; batching at a
#: conservative width keeps a large candidate set from depending on which
#: SQLite build the deployment happens to link against.
_PARAMETER_BATCH = 400


class SqliteVecIndex:
    """A ``MutableSimilarityIndexProtocol`` over a sqlite-vec ``vec0`` table.

    Args:
        connection: An open SQLite connection. Injected rather than opened
            here, so the deployment owns the file, the lifetime, and the
            transaction boundary — the same discipline the graph store follows.
            The sqlite-vec extension is loaded onto it at construction.
        embedder: The text-to-vector seam (D-IMPL-07). Injected, because which
            model a deployment embeds with is deployment configuration and the
            SDK ships no model.
        index_version: Version identity the deployment assigns to this corpus
            state. Composed with the embedder's ``model_version`` to form
            :attr:`index_version`; see that property.
        table: Vector table name. Defaults to :data:`DEFAULT_TABLE`.
    """

    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        embedder: EmbedderProtocol,
        index_version: str,
        table: str = DEFAULT_TABLE,
    ) -> None:
        self._connection = connection
        self._embedder = embedder
        self._corpus_version = index_version
        self._table = table
        self._load_extension()
        self._create_table()

    def _load_extension(self) -> None:
        self._connection.enable_load_extension(True)
        try:
            sqlite_vec.load(self._connection)
        finally:
            # Re-disabled unconditionally: leaving extension loading armed on a
            # connection the deployment goes on to use means arbitrary SQL on
            # that connection can load arbitrary shared objects.
            self._connection.enable_load_extension(False)

    def _create_table(self) -> None:
        self._connection.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {self._table} USING vec0("
            "tenant_id text partition key, "
            "entity_uri text, "
            f"embedding float[{self._embedder.dimensions}])"
        )
        self._connection.commit()

    @property
    def index_version(self) -> str:
        """The corpus version and the embedding model version, together.

        INV-CH7-27 names both in the determinism contract, and they are two
        independent ways for an answer to change: re-ingesting the corpus, and
        re-embedding it. A version identifying only one of them would let a
        replay resolve an index that agrees about its own name while disagreeing
        about every vector in it.
        """
        return f"{self._corpus_version}+{self._embedder.model_version}"

    def upsert(self, *, tenant_id: str, entity_uri: str, text: str) -> None:
        """Replace this tenant's vector for ``entity_uri`` with one for ``text``.

        Delete-then-insert rather than an UPDATE, because vec0 has no
        per-partition uniqueness to hang an upsert on (see the module
        docstring), and because it makes re-admission of identical text
        idempotent in the one way that matters: exactly one row survives.
        """
        embedding = self._embedder.embed(text=text)
        with self._connection:
            self._connection.execute(
                f"DELETE FROM {self._table} WHERE tenant_id = ? AND entity_uri = ?",
                (tenant_id, entity_uri),
            )
            self._connection.execute(
                f"INSERT INTO {self._table}(tenant_id, entity_uri, embedding)"
                " VALUES (?, ?, ?)",
                (tenant_id, entity_uri, sqlite_vec.serialize_float32(embedding)),
            )

    def delete(self, *, tenant_id: str, entity_uri: str) -> None:
        """Drop this tenant's vector for ``entity_uri``; a no-op when absent."""
        with self._connection:
            self._connection.execute(
                f"DELETE FROM {self._table} WHERE tenant_id = ? AND entity_uri = ?",
                (tenant_id, entity_uri),
            )

    def rank(
        self, *, tenant_id: str, query: str, candidates: tuple[str, ...]
    ) -> tuple[SimilarityHit, ...]:
        """Score exactly ``candidates`` against ``query`` within ``tenant_id``.

        Candidates absent from this tenant's corpus produce no row and are
        therefore omitted rather than scored zero — including candidates that
        another tenant has indexed under the same URI, which the partition key
        keeps out of the scan entirely.
        """
        if not candidates:
            return ()
        embedded = sqlite_vec.serialize_float32(self._embedder.embed(text=query))
        hits: list[SimilarityHit] = []
        # Deduplicated because a caller may repeat a candidate and a row would
        # then be scored twice, putting one entity in the result set twice.
        unique = tuple(dict.fromkeys(candidates))
        for start in range(0, len(unique), _PARAMETER_BATCH):
            batch = unique[start : start + _PARAMETER_BATCH]
            placeholders = ", ".join("?" * len(batch))
            rows = self._connection.execute(
                f"SELECT entity_uri, vec_distance_cosine(embedding, ?) FROM {self._table}"
                f" WHERE tenant_id = ? AND entity_uri IN ({placeholders})",
                (embedded, tenant_id, *batch),
            ).fetchall()
            hits.extend(
                SimilarityHit(
                    entity_uri=str(entity_uri),
                    score_percent=cosine_score_percent(float(distance)),
                )
                for entity_uri, distance in rows
            )
        return order_hits(hits)
