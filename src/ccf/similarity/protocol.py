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

**Two protocols, because the operator needs less than the fabric does.**
:class:`SimilarityIndexProtocol` is read-only, and that is deliberately all the
Similarity operator is typed against: an operator that could admit content to
the corpus would be a second writer wearing a different name (CLAUDE.md §10).
:class:`MutableSimilarityIndexProtocol` adds the corpus-admission surface —
``upsert`` and ``delete`` — and is what a deployment's assembly path holds. The
conformance suite runs against the mutable one because a suite that could not
populate a corpus could only test an index someone else had already built.

Corpus admission takes **text, not vectors**. The text-to-vector step lives
behind :mod:`ccf.similarity.embedder` (D-IMPL-07), so it belongs to the index
that chose an embedder, not to the caller. Taking vectors would also make the
lexical reference index unimplementable against the same Protocol, and one
shared conformance suite (D-16) is worth more than a vector-shaped signature.

The SDK ships three implementations behind this seam: :class:`TokenOverlapIndex`
here (deterministic, in-memory, no embedder), ``SqliteVecIndex`` (the dev
default, D-IMPL-03), and ``ChromaIndex`` (optional extra, D-13). The first is a
*reference*, not a recommendation: Jaccard overlap over whitespace tokens is
exactly enough to make the Similarity category genuine (it ranks, it
thresholds, it pins a version) and deliberately not enough to be mistaken for
production retrieval. The corpus every one of them ranks over is supplied by
the deployment — the SDK holds no corpus and no vocabulary (CLAUDE.md §11).

Algorithmic module (CINV-03): ranking here is lexical, never semantic. A
semantic index is a *different implementation of this Protocol*, living in its
own untagged module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "MutableSimilarityIndexProtocol",
    "SimilarityHit",
    "SimilarityIndexProtocol",
    "TokenOverlapIndex",
    "cosine_score_percent",
    "order_hits",
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


@runtime_checkable
class MutableSimilarityIndexProtocol(SimilarityIndexProtocol, Protocol):
    """A ranking index whose corpus a deployment can admit content to.

    Separate from :class:`SimilarityIndexProtocol` so the Similarity operator
    can be typed against the read-only half. An operator holding this Protocol
    could edit the corpus its own provenance pins a version of, which is the
    single-writer discipline (CLAUDE.md §10) failing one layer over.
    """

    def upsert(self, *, tenant_id: str, entity_uri: str, text: str) -> None:
        """Admit ``text`` as the current corpus content for ``entity_uri``.

        Replaces rather than accumulates, mirroring the graph's logical
        supersession: one URI holds one current text per tenant. An index that
        accumulated would keep answering from state the deployment had already
        superseded, and the caller would have no way to tell a stale hit from a
        fresh one.
        """
        ...

    def delete(self, *, tenant_id: str, entity_uri: str) -> None:
        """Remove ``entity_uri`` from the tenant's corpus.

        Idempotent: deleting something absent is a no-op, so a resumed
        supersession sweep is safe to re-run over ground it already covered.
        """
        ...


def cosine_score_percent(distance: float) -> int:
    """Render a cosine *distance* as an integer similarity percent.

    Shared by every vector-backed implementation, because both sqlite-vec and
    Chroma report ``1 - cos`` and two independent renderings of the same number
    would let a deployment's scores shift when it swapped substrates — with the
    operator's ``minimum_score_percent`` floor still set for the old one.

    Negative cosine (vectors pointing apart) is reported as 0 rather than as a
    negative score: "less than nothing in common" is not a distinction a
    percent floor can act on, and a negative integer on a percent scale invites
    exactly one arithmetic bug.

    A non-finite distance means at least one side was the zero vector — text
    the embedder had nothing to say about. That is 0 similarity, not an error:
    an empty document is *in the corpus and irrelevant*, which the contract
    already distinguishes from being absent.
    """
    if not math.isfinite(distance):
        return 0
    similarity = 1.0 - distance
    if similarity <= 0.0:
        return 0
    return min(SCORE_SCALE, int(round(similarity * SCORE_SCALE)))


def order_hits(hits: list[SimilarityHit]) -> tuple[SimilarityHit, ...]:
    """Impose the canonical total order: descending score, ascending URI.

    Shared by every implementation rather than re-derived by each, because
    "descending score" alone is a *partial* order and the residue is settled by
    whatever the substrate's iteration happened to do — a dict's insertion
    order here, a B-tree's key order there. Two conformant indexes would then
    disagree about a tie, and a replay comparing provenance bit for bit would
    call that a changed decision.
    """
    hits.sort(key=lambda hit: (-hit.score_percent, hit.entity_uri))
    return tuple(hits)


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
        index_version: Version identity the deployment assigns to this corpus
            state. Required, with no default — an unversioned index is one
            that cannot be replayed against (D-IMPL-38).
        corpus: Optional seed content, ``(tenant_id, entity_uri) -> text``.
            Supplied by the deployment; the SDK ships no corpus. Equivalent to
            an :meth:`upsert` per entry, and offered only because building a
            whole corpus in one expression reads better at a boot site.
    """

    def __init__(
        self,
        *,
        index_version: str,
        corpus: Mapping[tuple[str, str], str] | None = None,
    ) -> None:
        self._corpus: dict[tuple[str, str], str] = dict(corpus or {})
        self._index_version = index_version

    @property
    def index_version(self) -> str:
        return self._index_version

    def upsert(self, *, tenant_id: str, entity_uri: str, text: str) -> None:
        """Replace this tenant's corpus content for ``entity_uri``."""
        self._corpus[(tenant_id, entity_uri)] = text

    def delete(self, *, tenant_id: str, entity_uri: str) -> None:
        """Drop this tenant's corpus content for ``entity_uri``, if any."""
        self._corpus.pop((tenant_id, entity_uri), None)

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
        return order_hits(hits)
