"""``SimilarityIndexProtocol`` — the vendor-neutral ranking seam (D-IMPL-03).

Whitepaper §7.4 (Similarity as one of the four canonical operator categories);
DESIGN.md §2B.1. Two obligations make this a Protocol rather than a helper:

**Version pinning.** The whitepaper's determinism contract for Similarity is
``(corpus_version, embedding_model_version, query, threshold, policy_regime) ->
same result`` (INV-CH7-27). An index that cannot name the version it answered
from cannot participate in replay, so :attr:`SimilarityIndexProtocol.index_version`
is part of the contract and is pinned into the operator's provenance sub-chain
on every invocation — not logged, *carried*.

**Integer scores.** Scores are integer percent, never floats. The canonical
serializer refuses floats outright (they are not bit-stable across platforms),
and a similarity score that cannot be canonically serialized cannot appear in a
provenance chain that replay compares bit-for-bit.

The slice ships :class:`TokenOverlapIndex`, a deterministic in-memory reference
implementation. It is a *reference*, not a recommendation: Jaccard overlap over
whitespace tokens is exactly enough to make the Similarity category genuine
(it ranks, it thresholds, it pins a version) and deliberately not enough to be
mistaken for production retrieval. The corpus it ranks over is supplied by the
deployment — the SDK holds no corpus and no vocabulary (CLAUDE.md §11).

Algorithmic module (CINV-03): ranking here is lexical, never semantic. A
semantic index is a *different implementation of this Protocol*, living in its
own untagged module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "SimilarityHit",
    "SimilarityIndexProtocol",
    "TokenOverlapIndex",
]

#: Scores are expressed on this integer scale (percent). Named rather than
#: inlined so the arithmetic below and the threshold parameters an operator
#: declares are demonstrably on the same scale.
SCORE_SCALE = 100


class SimilarityHit(CCFContract):
    """One ranked candidate.

    Attributes:
        entity_uri: The ranked entity, addressed by its canonical URI — never
            by a backend row id, which would not survive a substrate change.
        score_percent: Integer score on the ``0..100`` scale. Integer by
            contract; see the module docstring.
    """

    entity_uri: str
    score_percent: int


@runtime_checkable
class SimilarityIndexProtocol(Protocol):
    """A corpus-scoped ranking index with a pinnable version (INV-CH7-27)."""

    @property
    def index_version(self) -> str:
        """Version identity of the corpus + model this index answers from.

        Pinned into the Similarity operator's provenance so a replay resolves
        the *same* index state, never "whatever the index holds now".
        """
        ...

    def rank(
        self, *, tenant_id: str, query: str, candidates: tuple[str, ...]
    ) -> tuple[SimilarityHit, ...]:
        """Rank ``candidates`` against ``query``, best first.

        ``candidates`` is the *already policy-filtered* candidate set: the
        Policy-before-Similarity ordering (INV-CH7-26) means an index never
        sees, and therefore can never rank, inadmissible content. Candidates
        absent from the corpus are omitted rather than scored zero — "not in
        the corpus" and "in the corpus and irrelevant" are different facts.
        """
        ...


class TokenOverlapIndex:
    """Deterministic in-memory reference index over deployment-supplied text.

    D-IMPL-03 reference implementation for the vertical slice. Scoring is
    Jaccard token overlap rendered as integer percent, computed with integer
    arithmetic so no float ever enters a canonically serialized artifact.

    Ordering is total and deterministic: descending score, then ascending
    ``entity_uri``. Ties broken by score alone would make the ranking
    dependent on dict iteration order, which is exactly the kind of incidental
    nondeterminism a bit-for-bit replay assertion catches at the worst moment.

    Args:
        corpus: ``(tenant_id, entity_uri) -> text``. Supplied by the
            deployment; the SDK ships no corpus.
        index_version: Version identity the deployment assigns to this corpus
            state. Required, with no default — an unversioned index is one
            that cannot be replayed against (D-IMPL-38).
    """

    def __init__(
        self,
        *,
        corpus: Mapping[tuple[str, str], str],
        index_version: str,
    ) -> None:
        self._corpus = dict(corpus)
        self._index_version = index_version

    @property
    def index_version(self) -> str:
        return self._index_version

    @staticmethod
    def _tokens(text: str) -> frozenset[str]:
        return frozenset(token for token in text.lower().split() if token)

    def rank(
        self, *, tenant_id: str, query: str, candidates: tuple[str, ...]
    ) -> tuple[SimilarityHit, ...]:
        """Rank ``candidates`` by integer Jaccard overlap with ``query``."""
        query_tokens = self._tokens(query)
        hits: list[SimilarityHit] = []
        for entity_uri in candidates:
            text = self._corpus.get((tenant_id, entity_uri))
            if text is None:
                continue
            tokens = self._tokens(text)
            union = query_tokens | tokens
            if not union:
                continue
            overlap = len(query_tokens & tokens)
            hits.append(
                SimilarityHit(
                    entity_uri=entity_uri,
                    score_percent=(overlap * SCORE_SCALE) // len(union),
                )
            )
        hits.sort(key=lambda hit: (-hit.score_percent, hit.entity_uri))
        return tuple(hits)
