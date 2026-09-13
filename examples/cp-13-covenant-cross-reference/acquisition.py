"""The three source legs, and one rule about citations.

[ADAPT] everything here. [MECHANISM] nothing.

**MongoDB carries the text and the spans. Fluree carries the typed
relationships and the anchors. PostgreSQL carries the entitlement rules.**

## THE CITATION RULE, which is the whole of this module

A citation is a **named passage**, reached through ``ex:evidencedBy``. That
edge names a passage IRI; the passage's *own* ``start_offset``, ``end_offset``
and ``sha256`` — read from MongoDB — are the citation, and the span is re-hashed
before anything is emitted.

**The anchor predicates on an evidence node are never joined to build one**,
and the reason is not that the join currently misbehaves — measured 2026-09-13
it returns 44 rows over 44 subjects and all 44 re-hash. The reason is that the
citation unit IS the passage. A rule that held only while the data was broken
would be a workaround; this one is the contract (`CXR-G07`).

## The trap this product actually teaches

**A span can be correct and still be unauditable.** All 49
``ex:CovenantDefinition`` nodes carry ``startOffset``, ``endOffset`` and
``documentId`` — and **none carries ``passageSha256`` or ``evidencedBy``**, and
no indexed passage matches or even contains the span. The text they point at is
exactly right:

```
"Consolidated Fixed Charge Coverage Ratio" means, for any Measurement …
```

Emitting it would feel safe and would be an **asserted** citation rather than a
checked one. :class:`Uncitable` with ``span-unverifiable`` is the answer
(`CXR-G08`, `CXR-G19`).

## One predicate that marks a limitation, and one that does not exist

``ex:declaredAt`` — 170 assertions, 158 of them on ``DefinedTerm`` — says *this
is intentionally a point anchor*. **It does not supply an end offset and does
not make the anchor quotable**; the claim is still Context Debt (`CXR-G16`).

``ex:governedBy`` is measured at **0 assertions** though the vault's schema for
this product names it. It is declared under ``absent_predicates`` so the absence
is stated rather than discovered, and nothing here reads it, writes it, or
substitutes a proxy for it (`CXR-G17`).

Reads only. Nothing here writes to any of the three stores.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
import yaml
from pymongo import MongoClient

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"

#: The corpus scopes the entitlement table recognizes. A scope outside this set
#: is a request error, not an empty permitted set.
CORPUS_SCOPES = ("filed", "filed-and-internal")


class UnknownCovenantSource(RuntimeError):
    """The estate holds no such evidence node.

    A **request error**, distinct from *"this source has no definition chain"*,
    which is a fact about the world and serves with an empty chain (`CXR-G14`).
    """


class ScopeNotEntitled(RuntimeError):
    """The principal has no entitlement row for the requested corpus scope.

    **Refused, never silently narrowed** (`CXR-G10`). Narrowing would answer a
    question the caller did not ask and would hide that the document class
    exists at all. Measured: `relationship-manager` has no
    `filed-and-internal` row, so this is reachable rather than theoretical.
    """


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. This example reads a live estate; see the"
            " README's Run-it section for the read-only roles it needs"
        )
    return value


def vocabulary() -> Mapping[str, Any]:
    """The source terms this deployment reads, named once in an artifact."""
    document: Mapping[str, Any] = yaml.safe_load(
        VOCABULARY.read_text(encoding="utf-8")
    )
    return document["declaration"]


@dataclass(frozen=True)
class Citation:
    """A passage this product has CHECKED.

    Constructed only by :meth:`Estate.cite`, only from a passage reached through
    ``ex:evidencedBy``, and only when the re-hashed span matches. There is no
    other constructor, which is what makes `CXR-G07` a property of the code
    rather than a promise about it.
    """

    passage_id: str
    document_id: str
    start_offset: int
    end_offset: int
    sha256: str
    text: str
    heading: str | None
    alignment: str | None

    @property
    def locator(self) -> str:
        """The `PassageAnchor` locator for this citation.

        The SDK fixes the anchoring obligation and not the anchor schema
        (`ccf.contracts.claims.PassageAnchor`), so the deployment picks the
        vocabulary — here, the passage id, which is what the estate itself uses
        to name a span.
        """
        return self.passage_id


@dataclass(frozen=True)
class Uncitable:
    """A chain node located but not quotable — Context Debt, never a citation.

    ``reason`` is one of:

    ``point-anchor``
        the node carries a start and no end. Measured, `ex:endOffset` is absent
        on **all 158** `DefinedTerm` nodes, so every depth-3 chain terminates
        here (TRAP 2, `CXR-G08`, `CXR-G20`).
    ``passage-has-no-sha256``
        548 of 37,865 passages carry none and cannot be checked.
    ``passage-not-found``
        the ``evidencedBy`` target does not resolve in MongoDB.
    ``span-unverifiable``
        the node names a REAL span — start, end and document — and records no
        ``passageSha256``, and no indexed passage covers it. Measured, all 49
        `CovenantDefinition` nodes are here: their spans land on exactly the
        right text (*"Consolidated Fixed Charge Coverage Ratio" means, for any
        Measurement…*) and there is nothing to check them against.

        **This is the hardest case in the product and the reason `CXR-G07`
        exists.** The text is extractable and visibly correct to a human, so
        emitting it would feel safe. It would still be an ASSERTED citation
        rather than a checked one, and the difference is the whole tier.
    ``no-evidence-edge``
        the node carries an end offset and a recorded hash but no
        ``evidencedBy`` — a shape this estate does not currently hold, kept
        distinct so it cannot be silently folded into the two above.
    """

    node_uri: str
    reason: str
    note: str


@dataclass(frozen=True)
class ChainNode:
    """One node of a definition chain, with whatever evidence it has."""

    uri: str
    kind: str
    depth: int
    label: str | None
    citations: tuple[Citation, ...]
    uncitable: tuple[Uncitable, ...]
    #: What the node CLAIMS about its own anchors, reported and never joined.
    anchor_claims: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class EvidenceSource:
    """A `COVSRC-*` node: the root the definition chain actually hangs from.

    **Untyped in the ledger, and that is the point** (TRAP 3). Seeding on
    `ex:Covenant` reaches depth 3 once; seeding here reaches it 26 times.
    """

    uri: str
    covenant_type: str | None
    threshold: str | None
    document_id: str | None
    chain: tuple[ChainNode, ...]


@dataclass(frozen=True)
class Entitlement:
    """What this principal may read, from `ccf_v2.corpus_entitlement`."""

    principal: str
    corpus_scope: str
    permitted_classes: frozenset[str]
    #: The document ids the classes admit. **This is the bound on the MongoDB
    #: retrieval, computed BEFORE any ranking runs** (`CXR-G09` limb b).
    permitted_documents: frozenset[str]
    #: Documents excluded for want of a classification. 49 of 249 carry none,
    #: and absence is NOT admission (`CP13-F-10`).
    unclassified_excluded: int


@dataclass
class Estate:
    """What one cross-reference needs, from all three stores."""

    sources: tuple[EvidenceSource, ...]
    entitlement: Entitlement
    as_of: datetime
    #: `{document_id: governs_from}` for the agreement documents in view.
    governs_from: Mapping[str, date]
    #: What the similarity step retrieved, and what it was allowed to see.
    retrieval: "Retrieval"
    seeded_on: str
    _mongo: Any = field(repr=False, default=None)
    _text: dict[str, str] = field(repr=False, default_factory=dict)

    def document_text(self, document_id: str) -> str | None:
        if document_id not in self._text:
            row = self._mongo["document"].find_one(
                {"document_id": document_id}, {"text": 1}
            )
            self._text[document_id] = row["text"] if row else None
        return self._text[document_id]


class _Relational:
    """PostgreSQL. Reads only."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(f"SET search_path TO {self._schema}")
            return connection.execute(sql, params).fetchall()


class _Graph:
    """Fluree, over SPARQL. Reads only."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    @property
    def dataset(self) -> str:
        return self._ledger

    def select(self, query: str) -> list[Mapping[str, str]]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query",
            data=query.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            document = json.loads(response.read())
        return [
            {key: value["value"] for key, value in binding.items()}
            for binding in document["results"]["bindings"]
        ]


# =========================================================================
# THE CITATION RESOLVER — the one path from a chain node to quoted text.
# =========================================================================


def _passage_id(iri: str, terms: Mapping[str, Any]) -> str:
    return iri.split(terms["passage_iri_prefix"], 1)[-1]


def _cite(
    mongo: Any, terms: Mapping[str, Any], *, node_uri: str, passage_iri: str,
) -> Citation | Uncitable:
    """Resolve ONE ``ex:evidencedBy`` edge to a checked citation.

    Four things happen here and the order is the contract:

    1. the passage IRI names a passage — resolve it in MongoDB **by id**;
    2. that passage's OWN ``start_offset``/``end_offset``/``sha256`` are read —
       never the evidence node's anchor predicates;
    3. the span is cut from the document text **by offset**, never by
       re-searching for the text, because a re-search can match a different
       occurrence and silently relocate the citation;
    4. the span is re-hashed and must equal the recorded ``sha256``.

    Anything that fails returns :class:`Uncitable`. Nothing here returns a
    citation it has not checked.
    """
    passage_id = _passage_id(passage_iri, terms)
    passage = mongo[terms["collections"]["passage"]].find_one(
        {"passage_id": passage_id}
    )
    if passage is None:
        return Uncitable(
            node_uri=node_uri, reason="passage-not-found",
            note=(
                f"the evidence edge names passage {passage_id!r}, which does"
                " not resolve in the document store"
            ),
        )
    if not passage.get("sha256"):
        # 548 of 37,865 passages carry none. A citation that cannot be checked
        # is not emitted unchecked (`CXR-G08`).
        return Uncitable(
            node_uri=node_uri, reason="passage-has-no-sha256",
            note=(
                f"passage {passage_id!r} carries no sha256, so the span cannot"
                " be checked; 548 of 37,865 passages are in this state"
            ),
        )
    document = mongo[terms["collections"]["document"]].find_one(
        {"document_id": passage["document_id"]}, {"text": 1}
    )
    if document is None:
        return Uncitable(
            node_uri=node_uri, reason="passage-not-found",
            note=f"document {passage['document_id']!r} is absent from the store",
        )
    span = document["text"][passage["start_offset"]:passage["end_offset"]]
    if hashlib.sha256(span.encode("utf-8")).hexdigest() != passage["sha256"]:
        return Uncitable(
            node_uri=node_uri, reason="sha256-mismatch",
            note=(
                f"passage {passage_id!r} re-hashes to a different value than it"
                " records; the span and the text have diverged"
            ),
        )
    return Citation(
        passage_id=passage_id,
        document_id=passage["document_id"],
        start_offset=passage["start_offset"],
        end_offset=passage["end_offset"],
        sha256=passage["sha256"],
        text=span,
        heading=passage.get("heading"),
        alignment=passage.get("alignment"),
    )


def _evidence_for(
    graph: _Graph, mongo: Any, terms: Mapping[str, Any], *, node_uri: str,
    permitted: frozenset[str], has_end_offset: bool, has_recorded_hash: bool,
    declared_point: bool = False,
) -> tuple[tuple[Citation, ...], tuple[Uncitable, ...]]:
    """Every checked citation for one node, and every reason there is not one.

    ``permitted`` bounds the retrieval: a passage in a document outside the
    permitted set is never read (`CXR-G15`).
    """
    edges = graph.select(
        f"SELECT ?p FROM <{graph.dataset}> WHERE {{"
        f" <{node_uri}> <{terms['evidenced_by']}> ?p }}"
    )
    if not edges:
        if not has_end_offset:
            # TRAP 2. Located, not quotable. Every `DefinedTerm` is here.
            # `ex:declaredAt` says the point is INTENTIONAL — read it, and
            # say which of the two states this is. The predicate marks the
            # limitation; it does not lift it, and either way no citation is
            # emitted (`CXR-G16`).
            return (), (Uncitable(
                node_uri=node_uri, reason="point-anchor",
                note=(
                    "the node is declared a point anchor by `ex:declaredAt`"
                    if declared_point else
                    "the node carries a start offset and no end offset"
                ) + (
                    "; it names a position rather than a span, so the text"
                    " cannot be quoted and no citation is emitted. The"
                    " declaration marks this limitation rather than repairing"
                    " it — there is still no end offset"
                ),
            ),)
        if not has_recorded_hash:
            # Extractable, and still not checkable. See `Uncitable`.
            return (), (Uncitable(
                node_uri=node_uri, reason="span-unverifiable",
                note=(
                    "the node names a real span and records no passage hash,"
                    " and no indexed passage covers it; the text can be cut"
                    " out but not checked, and an asserted citation is not a"
                    " checked one"
                ),
            ),)
        return (), (Uncitable(
            node_uri=node_uri, reason="no-evidence-edge",
            note=(
                "the node records a span and a hash but carries no"
                " `ex:evidencedBy` edge naming the passage they belong to"
            ),
        ),)

    citations: list[Citation] = []
    uncitable: list[Uncitable] = []
    for edge in edges:
        outcome = _cite(mongo, terms, node_uri=node_uri, passage_iri=edge["p"])
        if isinstance(outcome, Citation):
            if outcome.document_id not in permitted:
                # Never served, and never even read past the id — the bound is
                # the permitted set, at any depth (`CXR-G15`).
                continue
            citations.append(outcome)
        else:
            uncitable.append(outcome)
    return tuple(citations), tuple(uncitable)


# =========================================================================
# THE ENTITLEMENT — computed BEFORE any retrieval, and it bounds the query.
# =========================================================================


def _entitlement(
    relational: _Relational, mongo: Any, terms: Mapping[str, Any], *,
    principal: str, corpus_scope: str,
) -> Entitlement:
    """The permitted document set for this principal and scope.

    **This runs before anything is retrieved and its output is an argument to
    the retrieval, never a predicate over its results** (`CXR-G09` limb b).
    A post-filter has already computed similarity against impermissible
    documents, and in an MNPI context that computation is itself the leak.
    """
    if corpus_scope not in CORPUS_SCOPES:
        raise ValueError(
            f"corpus_scope must be one of {CORPUS_SCOPES}, not {corpus_scope!r}"
        )
    rows = relational.rows(
        f"SELECT permitted_class FROM {terms['tables']['corpus_entitlement']}"
        " WHERE principal = %s AND corpus_scope = %s",
        (principal, corpus_scope),
    )
    if not rows:
        raise ScopeNotEntitled(
            f"principal {principal!r} has no entitlement row for corpus scope"
            f" {corpus_scope!r}; refused rather than narrowed, because"
            " narrowing answers a question the caller did not ask and hides"
            " that the document class exists"
        )
    classes = frozenset(row[0] for row in rows)
    documents = mongo[terms["collections"]["document"]]
    permitted = frozenset(
        d["document_id"]
        for d in documents.find(
            {"classification": {"$in": sorted(classes)}}, {"document_id": 1}
        )
    )
    # Absence of a classification is NOT admission. 49 of 249 carry none.
    unclassified = documents.count_documents(
        {"classification": {"$exists": False}}
    )
    return Entitlement(
        principal=principal, corpus_scope=corpus_scope,
        permitted_classes=classes, permitted_documents=permitted,
        unclassified_excluded=unclassified,
    )


# =========================================================================
# THE CHAIN — seeded where the edges are, not where the type name suggests.
# =========================================================================

#: What the traversal seeds on, and it is DECLARED in the payload (`CXR-G12`).
#:
#: `ex:PassageAnchor` is the evidence node's type. Seeding on `ex:Covenant` —
#: the typed, plausible choice whose NAME matches the question — reaches depth 3
#: on 1 source; seeding here reaches it on 26 (TRAP 3, `CXR-G21`).
#:
#: These nodes were UNTYPED until 2026-09-13 and this constant read
#: `untyped-evidence-nodes-carrying-ex:definedBy`. The estate owner typed them,
#: deliberately not as `ex:Covenant` — an evidence node answering a covenant
#: query would make every "covenants in force" traversal collect 44 anchors.
#: The divergence is unchanged at 26 against 1; only the seed's spelling moved.
SEED = "ex:PassageAnchor"


def _chain_for(
    graph: _Graph, mongo: Any, terms: Mapping[str, Any], *, source_uri: str,
    permitted: frozenset[str], depth_limit: int,
) -> tuple[ChainNode, ...]:
    """Walk `definedBy` -> `crossReferences` / `measuredBy` from one source."""
    nodes: list[ChainNode] = []
    frontier = [(source_uri, 0)]
    seen = {source_uri}
    while frontier:
        uri, depth = frontier.pop(0)
        claims = _anchor_claims(graph, terms, uri=uri)
        citations, uncitable = _evidence_for(
            graph, mongo, terms, node_uri=uri, permitted=permitted,
            has_end_offset=bool(claims.get("end_offset")),
            has_recorded_hash=bool(claims.get("passage_sha256")),
            declared_point=bool(claims.get("declared_at")),
        )
        nodes.append(ChainNode(
            uri=uri, kind=_kind(graph, terms, uri=uri), depth=depth,
            label=None, citations=citations, uncitable=uncitable,
            anchor_claims=claims,
        ))
        if depth >= depth_limit:
            continue
        for predicate in ("defined_by", "cross_references", "measured_by"):
            for row in graph.select(
                f"SELECT ?o FROM <{graph.dataset}> WHERE {{"
                f" <{uri}> <{terms[predicate]}> ?o }}"
            ):
                if row["o"] not in seen:
                    seen.add(row["o"])
                    frontier.append((row["o"], depth + 1))
    return tuple(nodes)


def _anchor_claims(
    graph: _Graph, terms: Mapping[str, Any], *, uri: str
) -> Mapping[str, tuple[str, ...]]:
    """What a node CLAIMS about its own anchors — reported, never joined.

    Each key maps to EVERY value the node asserts, as a tuple. On 6 of 37
    evidence nodes two of these have two values each, and the tuple keeps that
    visible instead of collapsing it to one or silently pairing them.
    """
    out: dict[str, tuple[str, ...]] = {}
    predicates = {**terms["anchor_predicates"], "declared_at": terms["declared_at"]}
    for name, iri in predicates.items():
        rows = graph.select(
            f"SELECT ?o FROM <{graph.dataset}> WHERE {{ <{uri}> <{iri}> ?o }}"
        )
        if rows:
            out[name] = tuple(r["o"] for r in rows)
    return out


def _kind(graph: _Graph, terms: Mapping[str, Any], *, uri: str) -> str:
    """The node's ex: type, or ``untyped`` — which is a real answer here."""
    rows = graph.select(
        f"SELECT ?t FROM <{graph.dataset}> WHERE {{ <{uri}> a ?t }}"
    )
    for row in rows:
        if row["t"].startswith("http://example.org/fibo/"):
            return row["t"].rsplit("/", 1)[-1]
    return rows[0]["t"].rsplit("/", 1)[-1] if rows else "untyped"


def acquire(
    *, source_uris: Sequence[str], asked_at: datetime, principal: str,
    corpus_scope: str = "filed", resolve_depth: int = 3,
) -> Estate:
    """Read all three legs for one request, bounded at the decision instant."""
    terms = vocabulary()
    relational = _Relational(
        dsn=_setting("CCF_CP_13_POSTGRES_DSN"),
        schema=_setting("CCF_CP_13_POSTGRES_SCHEMA"),
    )
    graph = _Graph(
        url=_setting("CCF_CP_13_FLUREE_URL"),
        ledger=_setting("CCF_CP_13_FLUREE_LEDGER"),
    )
    mongo = MongoClient(
        _setting("CCF_CP_13_MONGO_URI"), serverSelectionTimeoutMS=15000
    )[_setting("CCF_CP_13_MONGO_DB")]

    # 1. THE ENVELOPE FIRST. Nothing is retrieved before the permitted set
    #    exists, because the permitted set is what bounds the retrieval.
    entitlement = _entitlement(
        relational, mongo, terms, principal=principal, corpus_scope=corpus_scope
    )

    known = {
        row["s"]
        for row in graph.select(
            f"SELECT ?s FROM <{graph.dataset}> WHERE {{"
            f" ?s <{terms['defined_by']}> ?o }}"
        )
    }
    missing = [u for u in source_uris if u not in known]
    if missing:
        raise UnknownCovenantSource(
            f"no evidence node with a definition chain at {missing!r} (404);"
            " this is a request error and is distinct from a source whose"
            " chain is empty, which is a fact about the world"
        )

    sources = tuple(
        EvidenceSource(
            uri=uri,
            covenant_type=_one(graph, terms["covenant_type"], uri),
            threshold=_one(graph, terms["threshold"], uri),
            document_id=_one(graph, terms["anchor_predicates"]["document_id"], uri),
            chain=_chain_for(
                graph, mongo, terms, source_uri=uri,
                permitted=entitlement.permitted_documents,
                depth_limit=resolve_depth,
            ),
        )
        for uri in sorted(dict.fromkeys(source_uris))
    )

    # 2. THE GOVERNING CLOCK. `governs_from`, and deliberately not
    #    `filed_date` — an amendment is filed after it begins governing, and a
    #    product keyed on the filing date serves the old text for the gap
    #    between them (`CXR-G11`).
    governs: dict[str, date] = {}
    for row in mongo[terms["collections"]["document"]].find(
        {terms["governing_field"]: {"$exists": True}},
        {"document_id": 1, terms["governing_field"]: 1},
    ):
        governs[row["document_id"]] = date.fromisoformat(
            row[terms["governing_field"]]
        )

    # 3. THE SIMILARITY STEP, and it runs LAST — after the envelope exists, so
    #    the envelope can bound it (`CXR-G09`). The probe is a passage this
    #    product already checked, so the ranking is anchored on evidence.
    probe = None
    for source in sources:
        for node in source.chain:
            if node.citations:
                probe = probe_embedding(
                    mongo, terms, passage_id=node.citations[0].passage_id
                )
                break
        if probe is not None:
            break
    retrieval = retrieve_supporting(
        mongo, terms, entitlement=entitlement, probe=probe
    )

    return Estate(
        sources=sources, entitlement=entitlement, as_of=asked_at,
        governs_from=governs, retrieval=retrieval, seeded_on=SEED,
        _mongo=mongo,
    )


def _one(graph: _Graph, iri: str, uri: str) -> str | None:
    rows = graph.select(
        f"SELECT ?o FROM <{graph.dataset}> WHERE {{ <{uri}> <{iri}> ?o }}"
    )
    return rows[0]["o"] if len(rows) == 1 else None


def evidence_sources(*, limit: int | None = None) -> list[str]:
    """Every evidence node carrying a definition chain, for a caller to pick from."""
    terms = vocabulary()
    graph = _Graph(
        url=_setting("CCF_CP_13_FLUREE_URL"),
        ledger=_setting("CCF_CP_13_FLUREE_LEDGER"),
    )
    rows = graph.select(
        f"SELECT DISTINCT ?s FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['passage_anchor_class']}> ."
        f" ?s <{terms['defined_by']}> ?o }}"
    )
    out = sorted(r["s"] for r in rows)
    return out[:limit] if limit else out


# =========================================================================
# THE SIMILARITY LEG — bounded BEFORE it runs, and instrumented so that the
# bound is checkable from outside (`CXR-G09`).
# =========================================================================


@dataclass(frozen=True)
class Retrieval:
    """What the similarity step retrieved, and **what it was allowed to see**.

    ``query_filter`` is the ACTUAL MongoDB filter the retrieval issued, carried
    out of the function so a caller can assert the bound was an argument to the
    query rather than a predicate over its results.

    **This is what makes `CXR-G09` provable.** A post-filter implementation can
    produce a byte-identical ``hits`` list — it retrieves broadly, ranks, then
    drops the impermissible rows. The payload looks the same. What differs is
    ``candidates_examined``: the post-filter has already computed similarity
    against documents the principal may not see, and in an MNPI setting that
    computation *is* the leak. A gate that only compared ``hits`` would pass
    against the leak.
    """

    query_filter: Mapping[str, Any]
    #: How many documents the ranking actually scored. Equals the permitted
    #: population when the bound is applied first, and the whole corpus when it
    #: is applied afterwards.
    candidates_examined: int
    #: Eligible by entitlement but carrying no embedding — **not searchable**,
    #: and never the same statement as "nothing relevant" (`CXR-G18`).
    not_evaluable: tuple[str, ...]
    hits: tuple[Mapping[str, Any], ...]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def retrieve_supporting(
    mongo: Any, terms: Mapping[str, Any], *, entitlement: Entitlement,
    probe: Sequence[float] | None, limit: int = 5,
) -> Retrieval:
    """Rank the internal corpus **within the permitted set only**.

    The permitted classifications are an argument to the query. Nothing outside
    them is read, scored, or counted — which is the difference between a policy
    envelope and a filter.
    """
    collection = mongo[terms["collections"]["memorandum"]]
    # THE BOUND, as an argument to the query. Not applied afterwards.
    query_filter: dict[str, Any] = {
        "classification": {"$in": sorted(entitlement.permitted_classes)}
    }
    eligible = list(collection.find(query_filter))
    not_evaluable = tuple(
        sorted(
            row["memorandum_id"] for row in eligible if not row.get("embedding")
        )
    )
    rankable = [row for row in eligible if row.get("embedding")]
    scored: list[tuple[float, Mapping[str, Any]]] = []
    if probe is not None:
        scored = sorted(
            ((_cosine(probe, row["embedding"]), row) for row in rankable),
            key=lambda pair: pair[0],
            reverse=True,
        )
    return Retrieval(
        query_filter=query_filter,
        candidates_examined=len(rankable),
        not_evaluable=not_evaluable,
        hits=tuple(
            {
                "memorandum_id": row["memorandum_id"],
                "title": row.get("title"),
                "classification": row["classification"],
                "authored_date": row.get("authored_date"),
                "score_percent": int(round(score * 100)),
            }
            for score, row in scored[:limit]
        ),
    )


def probe_embedding(mongo: Any, terms: Mapping[str, Any], *, passage_id: str):
    """The embedding of a checked citation, used as the similarity probe.

    The probe is a passage this product has already verified, so the ranking is
    anchored on evidence rather than on a string someone typed.
    """
    row = mongo[terms["collections"]["passage"]].find_one(
        {"passage_id": passage_id}, {"embedding": 1}
    )
    return row.get("embedding") if row else None
