"""``ChromaIndex`` — the second reference vector substrate (D-13, D-IMPL-03).

Whitepaper §7.4; CLAUDE.md §12 D-IMPL-03 ("a ``SimilarityIndex`` Protocol with
reference impls, or a single vendor?" — resolved as the Protocol) and §11
("Reference implementations ship alongside Protocols"). A Protocol with one
implementation is an interface nobody has tested against a second opinion, so
the second one is what makes the seam a claim rather than a promise: this class
and :class:`~ccf.similarity.sqlite_vec_index.SqliteVecIndex` pass the *same*
conformance suite, and the Similarity operator cannot tell which it is holding.

**chromadb is never a core dependency.** Its transitive tree pulls
onnxruntime, opentelemetry, and the Kubernetes client, which is both an install
burden and supply-chain surface a fabric SDK has no business imposing on a
deployment that chose sqlite-vec (T-04-26). It is the ``chroma`` optional
extra, and the import lives *inside* :meth:`__init__` so that ``import ccf``,
and even ``import ccf.similarity.chroma_index``, succeed in an environment
without it. Constructing the class is the first moment the dependency is
needed, and the first moment it is demanded.

Two shape decisions, verified against chromadb 1.5.9:

* **One collection per tenant, named by digest.** Chroma constrains collection
  names to 3–512 characters of ``[a-zA-Z0-9._-]``, which a tenant identifier is
  under no obligation to satisfy — so the name is a prefix plus a SHA-256
  digest of the tenant id rather than the id itself. Per-tenant collections
  rather than one collection with a ``tenant_id`` metadata filter because
  isolation belongs in the storage layout: a forgotten ``where`` clause is a
  cross-tenant disclosure (T-04-25), and a collection a query never opened is
  not one it can leak from.
* **Ranking restricts the search to the supplied candidate ids.** Policy runs
  before Similarity (INV-CH7-26), so the candidate set is already the answer's
  universe; searching wider and intersecting afterwards would silently drop
  admissible candidates that lost to inadmissible ones.

Not tagged ``__ccf_mode__ = "algorithmic"``: this module invokes an
:class:`~ccf.similarity.embedder.EmbedderProtocol`, and an embedding model is a
semantic stage.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ccf.similarity.embedder import EmbedderProtocol
from ccf.similarity.protocol import (
    SimilarityHit,
    cosine_score_percent,
    order_hits,
)

__all__ = ["COLLECTION_PREFIX", "ChromaIndex"]

#: Prefix for derived collection names. Satisfies Chroma's "starts with an
#: alphanumeric" rule and keeps CCF's collections identifiable in a Chroma
#: instance a deployment also uses for something else.
COLLECTION_PREFIX = "ccf-"

#: Chroma computes distances under a per-collection space; cosine is the one
#: :func:`~ccf.similarity.protocol.cosine_score_percent` renders, and it must
#: match what sqlite-vec's ``vec_distance_cosine`` returns or the two backends
#: would score the same corpus differently.
_COSINE_CONFIGURATION = {"hnsw": {"space": "cosine"}}


def _collection_name(tenant_id: str) -> str:
    """Derive a Chroma-legal collection name from an arbitrary tenant id.

    A digest rather than a sanitizing transform, because sanitizing is not
    injective: two tenant ids differing only in characters Chroma rejects would
    collapse onto one collection, which is a cross-tenant merge produced by a
    naming convention.
    """
    return COLLECTION_PREFIX + hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()


class ChromaIndex:
    """A ``MutableSimilarityIndexProtocol`` over a Chroma client.

    Args:
        embedder: The text-to-vector seam (D-IMPL-07). Injected; Chroma's own
            default embedding function is deliberately never used, because it
            would put a model the deployment did not choose — and cannot name a
            version for — inside the INV-CH7-27 determinism contract.
        index_version: Version identity the deployment assigns to this corpus
            state. Composed with the embedder's ``model_version``; see
            :attr:`index_version`.
        path: Directory for a ``PersistentClient``. ``None`` selects an
            ``EphemeralClient``, which is what the conformance suite uses and
            what a deployment should use for nothing else.

    Raises:
        ModuleNotFoundError: When the ``chroma`` extra is not installed. Raised
            here rather than at import so the module remains importable and the
            failure names the moment a deployment actually asked for Chroma.
    """

    def __init__(
        self,
        *,
        embedder: EmbedderProtocol,
        index_version: str,
        path: Path | None = None,
    ) -> None:
        import chromadb  # noqa: PLC0415 - lazy by design; see the module docstring

        self._embedder = embedder
        self._corpus_version = index_version
        self._client: Any = (
            chromadb.PersistentClient(path=str(path))
            if path is not None
            else chromadb.EphemeralClient()
        )

    @property
    def index_version(self) -> str:
        """The corpus version and the embedding model version, together.

        INV-CH7-27 names both, and they are two independent ways for an answer
        to change: re-ingesting the corpus, and re-embedding it.
        """
        return f"{self._corpus_version}+{self._embedder.model_version}"

    def _collection(self, tenant_id: str) -> Any:
        return self._client.get_or_create_collection(
            _collection_name(tenant_id), configuration=_COSINE_CONFIGURATION
        )

    def upsert(self, *, tenant_id: str, entity_uri: str, text: str) -> None:
        """Replace this tenant's vector for ``entity_uri`` with one for ``text``."""
        self._collection(tenant_id).upsert(
            ids=[entity_uri], embeddings=[list(self._embedder.embed(text=text))]
        )

    def delete(self, *, tenant_id: str, entity_uri: str) -> None:
        """Drop this tenant's vector for ``entity_uri``; a no-op when absent."""
        self._collection(tenant_id).delete(ids=[entity_uri])

    def rank(
        self, *, tenant_id: str, query: str, candidates: tuple[str, ...]
    ) -> tuple[SimilarityHit, ...]:
        """Score exactly ``candidates`` against ``query`` within ``tenant_id``.

        Candidates absent from this tenant's collection come back absent rather
        than at distance infinity, which is what keeps "not in the corpus"
        distinguishable from "in the corpus and irrelevant".

        Chroma 1.5.9 raises ``InternalError: Error finding id`` when a
        ``query(ids=...)`` restriction names an id the collection does not
        hold, so the present ids are resolved first and the search is
        restricted to those. The extra round trip is the price of the substrate
        being strict where the Protocol is tolerant; the alternative — letting
        the error escape — would make "this candidate is not in the corpus"
        into a failure rather than into an omission, and the two mean opposite
        things to a caller.
        """
        if not candidates:
            return ()
        # Deduplicated because Chroma would otherwise return the id once per
        # occurrence and a caller who repeated a candidate would see it twice.
        unique = list(dict.fromkeys(candidates))
        collection = self._collection(tenant_id)
        held = set(collection.get(ids=unique, include=[])["ids"])
        present = [entity_uri for entity_uri in unique if entity_uri in held]
        if not present:
            return ()
        result = collection.query(
            query_embeddings=[list(self._embedder.embed(text=query))],
            ids=present,
            n_results=len(present),
            include=["distances"],
        )
        ids: list[str] = list(result["ids"][0])
        distances: list[float] = list(result["distances"][0])
        return order_hits(
            [
                SimilarityHit(
                    entity_uri=str(entity_uri),
                    score_percent=cosine_score_percent(float(distance)),
                )
                for entity_uri, distance in zip(ids, distances, strict=True)
            ]
        )
