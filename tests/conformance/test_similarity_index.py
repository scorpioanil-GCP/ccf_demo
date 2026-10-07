"""The ``SimilarityIndex`` conformance suite — the acceptance bar for D-IMPL-03.

Whitepaper §7.4 fixes what a Similarity substrate owes the fabric: a
corpus-scoped ranking whose determinism contract is ``(corpus_version,
embedding_model_version, query, threshold, policy_regime) -> same result``
(INV-CH7-27). CLAUDE.md §11 fixes the rest: the substrate is a Protocol with
more than one reference implementation, and the operator above it must not be
able to tell which one it is holding.

This module asserts that once, parametrized over an index factory (D-16,
mirroring ``tests/conformance/test_graphstore.py`` and
``tests/conformance/test_artifactstore.py``). Every implementation the SDK
ships — the lexical in-memory reference, sqlite-vec, Chroma — passes the *same*
bodies. A backend that needed its own assertions would be a backend the
operator could distinguish.

Three disciplines are load-bearing here:

* **No assertion is about an absolute score.** Jaccard overlap and cosine
  similarity produce different numbers for the same corpus; what the fabric
  depends on is the *ordering*, the integer scale, and the determinism. A suite
  that pinned scores would pass on one backend by construction and be
  unsatisfiable on the next.
* **Tenancy is asserted as absence, not as filtering.** T-04-25 is an
  information-disclosure threat: it is not enough that the wrong tenant's hit
  ranks last, it must not be in the result at all, and the same URI must be
  able to hold different content in two tenants without either leaking.
* **Determinism is asserted twice over.** Once for tie-breaking (equal scores
  must not depend on storage iteration order) and once for repetition (the same
  question asked twice gets the same answer), because a bit-for-bit replay
  assertion is what catches the difference, at the worst possible moment.

The embedder here is a deterministic hashing fake. No model call happens in
I.1 — the point of the ``EmbedderProtocol`` seam (D-IMPL-07) is that the vector
backends can be conformance-tested without one.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sqlite3
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ccf.similarity.embedder import EmbedderProtocol
from ccf.similarity.protocol import (
    SCORE_SCALE,
    MutableSimilarityIndexProtocol,
    SimilarityIndexProtocol,
    TokenOverlapIndex,
)
from ccf.similarity.sqlite_vec_index import SqliteVecIndex

pytestmark = pytest.mark.conformance

TENANT = "tenant-conformance"
OTHER_TENANT = "tenant-elsewhere"
INDEX_VERSION = "corpus-2026-07-25"

#: A query and a corpus chosen so that lexical overlap and vector cosine agree
#: about the *order*. They disagree about the numbers, which is exactly why no
#: assertion below reads one.
QUERY = "alpha beta"
NEAR = "alpha beta gamma"
MID = "alpha delta"
FAR = "epsilon zeta"


class _HashingEmbedder:
    """Deterministic bag-of-tokens embedder — a test double, never shipped.

    Each whitespace token contributes 1.0 to the dimension its SHA-256 digest
    selects, so texts sharing tokens share direction and cosine ranks them the
    way lexical overlap does. Hashing is SHA-256 rather than :func:`hash`
    because ``PYTHONHASHSEED`` randomizes the latter per process, and an
    embedder whose output moved between runs would make the determinism
    assertions below vacuous rather than failing.
    """

    model_version = "hashing-fake-1"

    def __init__(self, *, dimensions: int = 64) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, *, text: str) -> tuple[float, ...]:
        vector = [0.0] * self._dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:8], "big") % self._dimensions] += 1.0
        return tuple(vector)


IndexFactory = Callable[[], MutableSimilarityIndexProtocol]


def _chroma_param() -> object:
    """The Chroma param, carrying its own marker and its own skip condition.

    Both live on the param rather than on the tests so that ``-m chroma``
    selects the Chroma leg *of every test in this module* — the point of one
    parametrized suite (D-16) is that the backend is the axis, and a
    module-level marker would have made it the whole module.
    """
    return pytest.param(
        "chroma",
        marks=(
            pytest.mark.chroma,
            pytest.mark.skipif(
                importlib.util.find_spec("chromadb") is None,
                reason="the optional `chroma` extra is not installed"
                " — install the `chroma` extra from the source the SDK came"
                " from (`pip install -e \".[chroma]\"` in a checkout; never by"
                " bare name from public PyPI) to run this leg",
            ),
        ),
    )


@pytest.fixture(params=["token-overlap", "sqlite-vec", _chroma_param()])
def index_factory(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[IndexFactory]:
    """A factory for the index under test, one param per implementation.

    A factory rather than an instance so a test can build a second index over
    the same substrate without knowing what the substrate is. Chroma adds its
    param here; the test bodies below do not change.
    """
    if request.param == "token-overlap":

        def token_overlap_factory() -> MutableSimilarityIndexProtocol:
            return TokenOverlapIndex(index_version=INDEX_VERSION)

        yield token_overlap_factory
        return

    if request.param == "sqlite-vec":
        connections: list[sqlite3.Connection] = []
        database = tmp_path / "similarity.sqlite3"

        def sqlite_vec_factory() -> MutableSimilarityIndexProtocol:
            connection = sqlite3.connect(database)
            connections.append(connection)
            return SqliteVecIndex(
                connection=connection,
                embedder=_HashingEmbedder(),
                index_version=INDEX_VERSION,
            )

        yield sqlite_vec_factory
        for connection in connections:
            connection.close()
        return

    if request.param == "chroma":
        from ccf.similarity.chroma_index import ChromaIndex

        store = tmp_path / "chroma"

        def chroma_factory() -> MutableSimilarityIndexProtocol:
            return ChromaIndex(
                embedder=_HashingEmbedder(),
                index_version=INDEX_VERSION,
                path=store,
            )

        yield chroma_factory
        return

    raise NotImplementedError(request.param)


@pytest.fixture
def index(index_factory: IndexFactory) -> MutableSimilarityIndexProtocol:
    """An index preloaded with the shared corpus, in both tenants."""
    built = index_factory()
    built.upsert(tenant_id=TENANT, entity_uri="urn:near", text=NEAR)
    built.upsert(tenant_id=TENANT, entity_uri="urn:mid", text=MID)
    built.upsert(tenant_id=TENANT, entity_uri="urn:far", text=FAR)
    built.upsert(tenant_id=OTHER_TENANT, entity_uri="urn:other-only", text=NEAR)
    return built


ALL = ("urn:near", "urn:mid", "urn:far")


def _ranked_uris(
    index: SimilarityIndexProtocol,
    *,
    tenant_id: str = TENANT,
    query: str = QUERY,
    candidates: tuple[str, ...] = ALL,
) -> tuple[str, ...]:
    return tuple(
        hit.entity_uri
        for hit in index.rank(
            tenant_id=tenant_id, query=query, candidates=candidates
        )
    )


# --- the ranking contract --------------------------------------------------


def test_the_index_conforms_to_both_protocols_structurally(
    index: MutableSimilarityIndexProtocol,
) -> None:
    assert isinstance(index, SimilarityIndexProtocol)
    assert isinstance(index, MutableSimilarityIndexProtocol)


def test_candidates_are_ranked_best_first(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """Ordering, not scoring, is what the operator above depends on."""
    assert _ranked_uris(index) == ("urn:near", "urn:mid", "urn:far")


def test_scores_are_integers_on_the_declared_scale(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """Integer percent by contract — the canonical serializer refuses floats.

    A score that cannot be canonically serialized cannot appear in a provenance
    chain a replay compares bit for bit, so this is a contract of the substrate
    rather than a formatting choice at the edge.
    """
    hits = index.rank(tenant_id=TENANT, query=QUERY, candidates=ALL)
    for hit in hits:
        assert type(hit.score_percent) is int
        assert 0 <= hit.score_percent <= SCORE_SCALE


def test_a_closer_candidate_scores_at_least_as_high_as_a_farther_one(
    index: MutableSimilarityIndexProtocol,
) -> None:
    scores = {
        hit.entity_uri: hit.score_percent
        for hit in index.rank(tenant_id=TENANT, query=QUERY, candidates=ALL)
    }
    assert scores["urn:near"] > scores["urn:far"]
    assert scores["urn:mid"] > scores["urn:far"]


def test_only_requested_candidates_are_ranked(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """The candidate set is the policy-filtered set (INV-CH7-26).

    Policy runs before Similarity precisely so an index never sees inadmissible
    content. An index that widened its own candidate set would be re-admitting
    what Policy removed.
    """
    assert _ranked_uris(index, candidates=("urn:near",)) == ("urn:near",)


def test_an_empty_candidate_set_ranks_to_nothing(
    index: MutableSimilarityIndexProtocol,
) -> None:
    assert index.rank(tenant_id=TENANT, query=QUERY, candidates=()) == ()


def test_a_candidate_absent_from_the_corpus_is_omitted_not_scored_zero(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """"Not in the corpus" and "in the corpus and irrelevant" differ.

    Scoring an unknown URI zero would let a caller conclude the index had
    considered it. It did not, and the difference is what an auditor asking
    "was this ranked?" needs to be able to see.
    """
    ranked = _ranked_uris(index, candidates=("urn:near", "urn:never-indexed"))
    assert ranked == ("urn:near",)


# --- determinism (INV-CH7-27) ----------------------------------------------


def test_equal_scores_break_ties_on_ascending_entity_uri(
    index_factory: IndexFactory,
) -> None:
    """Ties broken by score alone would depend on storage iteration order.

    Which is the kind of incidental nondeterminism that survives every test run
    until the one where a replay compares two provenance chains bit for bit.
    """
    built = index_factory()
    for entity_uri in ("urn:zeta", "urn:alpha", "urn:mu"):
        built.upsert(tenant_id=TENANT, entity_uri=entity_uri, text=NEAR)
    ranked = _ranked_uris(built, candidates=("urn:zeta", "urn:alpha", "urn:mu"))
    assert ranked == ("urn:alpha", "urn:mu", "urn:zeta")


def test_the_same_question_asked_twice_gets_the_same_answer(
    index: MutableSimilarityIndexProtocol,
) -> None:
    first = index.rank(tenant_id=TENANT, query=QUERY, candidates=ALL)
    second = index.rank(tenant_id=TENANT, query=QUERY, candidates=ALL)
    assert first == second


def test_candidate_ordering_does_not_change_the_result(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """The candidate set is a set; the caller's tuple order is incidental."""
    forward = index.rank(tenant_id=TENANT, query=QUERY, candidates=ALL)
    backward = index.rank(tenant_id=TENANT, query=QUERY, candidates=tuple(reversed(ALL)))
    assert forward == backward


def test_the_index_version_is_stable_and_non_empty(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """An unversioned index is one that cannot be replayed against (D-IMPL-38)."""
    assert index.index_version
    assert index.index_version == index.index_version
    assert INDEX_VERSION in index.index_version


# --- tenancy (T-04-25) -----------------------------------------------------


def test_another_tenants_entity_is_never_ranked(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """Absent from the result, not merely ranked last."""
    assert _ranked_uris(index, candidates=("urn:near", "urn:other-only")) == (
        "urn:near",
    )


def test_one_uri_holds_independent_content_in_two_tenants(
    index_factory: IndexFactory,
) -> None:
    """Tenancy scopes identity, so the same URI is two different entities.

    If it did not, one tenant's upsert would silently overwrite another's
    corpus entry — an integrity failure that reads as an information-disclosure
    one the moment either tenant ranks.
    """
    built = index_factory()
    built.upsert(tenant_id=TENANT, entity_uri="urn:shared", text=NEAR)
    built.upsert(tenant_id=OTHER_TENANT, entity_uri="urn:shared", text=FAR)
    ours = built.rank(tenant_id=TENANT, query=QUERY, candidates=("urn:shared",))
    theirs = built.rank(
        tenant_id=OTHER_TENANT, query=QUERY, candidates=("urn:shared",)
    )
    assert ours[0].score_percent > theirs[0].score_percent


def test_deleting_in_one_tenant_leaves_the_other_intact(
    index_factory: IndexFactory,
) -> None:
    built = index_factory()
    built.upsert(tenant_id=TENANT, entity_uri="urn:shared", text=NEAR)
    built.upsert(tenant_id=OTHER_TENANT, entity_uri="urn:shared", text=NEAR)
    built.delete(tenant_id=TENANT, entity_uri="urn:shared")
    assert _ranked_uris(built, candidates=("urn:shared",)) == ()
    assert _ranked_uris(
        built, tenant_id=OTHER_TENANT, candidates=("urn:shared",)
    ) == ("urn:shared",)


# --- corpus admission and supersession -------------------------------------


def test_upsert_replaces_rather_than_accumulates(
    index_factory: IndexFactory,
) -> None:
    """Supersession, matching the graph: one URI holds one current text.

    An index that accumulated would keep answering from state the deployment
    has already superseded — a stale hit with no way for the caller to know it
    was stale.
    """
    built = index_factory()
    built.upsert(tenant_id=TENANT, entity_uri="urn:mutable", text=NEAR)
    before = built.rank(tenant_id=TENANT, query=QUERY, candidates=("urn:mutable",))
    built.upsert(tenant_id=TENANT, entity_uri="urn:mutable", text=FAR)
    after = built.rank(tenant_id=TENANT, query=QUERY, candidates=("urn:mutable",))
    assert len(after) == 1
    assert after[0].score_percent < before[0].score_percent


def test_re_upserting_identical_text_is_idempotent(
    index_factory: IndexFactory,
) -> None:
    built = index_factory()
    built.upsert(tenant_id=TENANT, entity_uri="urn:same", text=NEAR)
    first = built.rank(tenant_id=TENANT, query=QUERY, candidates=("urn:same",))
    built.upsert(tenant_id=TENANT, entity_uri="urn:same", text=NEAR)
    assert built.rank(tenant_id=TENANT, query=QUERY, candidates=("urn:same",)) == first


def test_a_deleted_entity_disappears_from_results(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """No silent stale hits — deletion is removal, not a score of zero."""
    index.delete(tenant_id=TENANT, entity_uri="urn:near")
    assert _ranked_uris(index) == ("urn:mid", "urn:far")


def test_deleting_an_entity_that_was_never_indexed_is_a_no_op(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """Idempotent so a re-run of a supersession sweep is safe.

    Raising here would make the caller's error handling depend on whether a
    previous sweep had already completed, which is exactly the state a
    resumable pipeline cannot know.
    """
    index.delete(tenant_id=TENANT, entity_uri="urn:never-indexed")
    assert _ranked_uris(index) == ("urn:near", "urn:mid", "urn:far")


# --- the embedder seam (D-IMPL-07) -----------------------------------------


def test_the_test_embedder_conforms_to_the_protocol_structurally() -> None:
    """The seam is real: a fake satisfies it without a model call.

    Which is the whole point of D-IMPL-07 — the vector backends are
    conformance-testable in I.1, where no LLM or embedding model exists yet.
    """
    assert isinstance(_HashingEmbedder(), EmbedderProtocol)


# --- the algebra above the seam --------------------------------------------


def test_composition_is_preserved_whichever_backend_ranks(
    index_factory: IndexFactory,
) -> None:
    """``(A∘B)(G) = A(B(G))`` holds with *any* conformant index underneath.

    The composition-preservation suite (``tests/properties/test_composition.py``)
    runs the Similarity operator over the in-memory reference index. That leaves
    one thing unasserted that D-IMPL-03 actually claims: the property is a
    property of the *operator*, not of the substrate that happened to be behind
    it. So the same assertion is made here once per shipped backend, over the
    corpus and the curated graphs the property suite uses.

    An index that consulted mutable state between the two invocations — a cache
    keyed on the last query, a connection that saw an interleaved write — would
    fail here and pass everywhere else.
    """
    from ccf.contracts.canonical import canonical_bytes
    from ccf.operators.categories import SimilaritySelect, TemporalAsOf
    from ccf.operators.params import SimilaritySelectParameters, TemporalAsOfParameters
    from ccf.operators.planner import IntermediateCache, compose
    # ``tests/`` carries no ``__init__.py``, so pytest's rootdir insertion makes
    # the suite packages importable by their bare names. Imported inside the
    # test rather than at module scope to keep the conformance suite's imports
    # a statement about the SDK, not about its other test packages.
    from properties.strategies import (
        BOUNDARY,
        CONTROL,
        TENANT as PROPERTY_TENANT,
        _corpus,
        curated_edge_graphs,
    )

    backend = index_factory()
    for (tenant_id, entity_uri), text in _corpus().items():
        backend.upsert(tenant_id=tenant_id, entity_uri=entity_uri, text=text)

    declared = CONTROL["operator_parameters"]
    similarity = SimilaritySelect(
        parameters=SimilaritySelectParameters(
            query=declared["similarity"]["query"],
            minimum_score_percent=declared["similarity"]["minimum_score_percent"],
            ranked_entity_classes=frozenset(
                declared["similarity"]["ranked_entity_classes"]
            ),
        ),
        index=backend,
    )
    temporal = TemporalAsOf(
        parameters=TemporalAsOfParameters(
            require_valid_at_boundary=declared["temporal"]["require_valid_at_boundary"]
        )
    )

    for curated in curated_edge_graphs():
        for outer, inner in ((similarity, temporal), (temporal, similarity)):
            composed = compose(outer, inner, cache=IntermediateCache()).apply(
                view=curated.view,
                tenant_id=PROPERTY_TENANT,
                temporal_boundary=BOUNDARY,
                upstream=(),
            )
            intermediate = inner.apply(
                view=curated.view,
                tenant_id=PROPERTY_TENANT,
                temporal_boundary=BOUNDARY,
                upstream=(),
            )
            direct = outer.apply(
                view=intermediate.view,
                tenant_id=PROPERTY_TENANT,
                temporal_boundary=BOUNDARY,
                upstream=(intermediate.provenance,),
            )
            assert canonical_bytes(composed) == canonical_bytes(direct)


def test_the_operator_pins_whichever_index_version_it_was_given(
    index: MutableSimilarityIndexProtocol,
) -> None:
    """INV-CH7-27: provenance carries the index version, whatever backend it is.

    Pinned rather than logged — a replay resolves the index state the decision
    was made against, and a version that lived only in a log line would not
    travel with the decision.
    """
    from ccf.operators.categories import SimilaritySelect
    from ccf.operators.params import SimilaritySelectParameters

    operator = SimilaritySelect(
        parameters=SimilaritySelectParameters(
            query=QUERY, minimum_score_percent=1, ranked_entity_classes=frozenset()
        ),
        index=index,
    )
    assert operator._index.index_version == index.index_version


# --- chromadb stays optional (T-04-26) -------------------------------------


def test_the_chroma_module_imports_without_chromadb_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``import ccf`` must not depend on the optional extra.

    Asserted by blocking ``chromadb`` at the import machinery and re-importing
    the module from a cleared cache — which reproduces an environment without
    the extra without requiring a second venv to run the suite in. The failure
    it catches is a top-level ``import chromadb`` creeping back in, and that
    failure is silent in any environment where the extra happens to be present.
    """
    blocked = "chromadb"

    class _Blocker:
        def find_module(self, name: str, path: object = None) -> None:
            return None

        def find_spec(
            self, name: str, path: object = None, target: object = None
        ) -> None:
            if name == blocked or name.startswith(f"{blocked}."):
                raise ModuleNotFoundError(f"No module named {blocked!r}")
            return None

    monkeypatch.setitem(sys.modules, blocked, None)  # type: ignore[misc]
    for module in [name for name in sys.modules if name.startswith(blocked)]:
        monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.syspath_prepend("")
    monkeypatch.setattr(sys, "meta_path", [_Blocker(), *sys.meta_path])

    for module in [
        name for name in sys.modules if name == "ccf" or name.startswith("ccf.")
    ]:
        monkeypatch.delitem(sys.modules, module, raising=False)

    importlib.import_module("ccf")
    chroma_module = importlib.import_module("ccf.similarity.chroma_index")

    with pytest.raises(ModuleNotFoundError):
        chroma_module.ChromaIndex(
            embedder=_HashingEmbedder(), index_version=INDEX_VERSION
        )
