"""The two source legs, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**, which is the clearest statement of what it is: somebody else's stores,
read the way those stores want to be read. It opens two systems of record,
walks one, joins the other, and hands back what it found.

**Its boundaries are ruled, not stylistic** (`D-IMPL-315`). This layer handles
*vocabulary, source access and admission*. It does not bind request values onto
Control Plane declarations, does not run gates, does not build a replay record
and does not serve. Those belong to `GovernedResolver`, which `produce.py` hands
the seam to; a helpful local shortcut here is the exact defect the successor
exists to not have.

**Two stores, and neither is complete on its own.** The family edges, the FIBO
class chain, the labels and the LEIs live in the graph leg. The GLEIF Level 1
attributes live in the relational leg, keyed by LEI. No schema author has joined
them, and most of this family's nodes do not appear in the relational leg at
all — which is not a defect to repair but the measured fact the product's
Context Debt is computed from.

**Batched per hop, never per node.** The walk issues one query per level of
depth against the whole frontier, and the attribute join issues exactly one
query for the entire collected key set. A per-node fan-out returns the same
answer and collapses at depth 4, so the difference never shows up in the payload
— only in the load, and only in production.

**Admission is where `family_id` is minted.** A node's family membership is
OBSERVED — it is true because this walk reached that node from this anchor —
rather than inherited from the anchor or joined in from the attribute leg. That
is what makes it usable as the policy envelope's axis: the alternative is
stamping an attribute onto nodes no source ever asserted it about, which makes a
policy check look populated while measuring nothing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

HERE = Path(__file__).parent

#: How long a single source read may take before this deployment gives up. A
#: read that hangs forever is a run that never reports which store was slow.
READ_TIMEOUT_SECONDS = 120


def _document(path: Path) -> Mapping[str, Any]:
    """One YAML document, parsed. The only file reading in this module."""
    parsed: Mapping[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed


def vocabulary() -> Mapping[str, Any]:
    """The sources' own names — IRIs, table and columns.

    Read from `artifacts/source-vocabulary.yaml` rather than written here, so
    pointing this example at another estate is an edit to a document instead of
    an edit to a program (CLAUDE.md §6.4).
    """
    declaration: Mapping[str, Any] = _document(
        HERE / "artifacts" / "source-vocabulary.yaml"
    )["declaration"]
    return declaration


@dataclass(frozen=True)
class Node:
    """One entity the walk admitted, in the source's own vocabulary."""

    uri: str
    lei: str | None
    label: str | None
    #: The FIBO class chain, served on every node. It is payload rather than an
    #: admission filter: nothing is excluded for the class it carries.
    type_chain: tuple[str, ...]
    #: Hops from the anchor at the moment of admission. The anchor is 0.
    depth: int


@dataclass(frozen=True)
class Edge:
    """One family relationship, under the FABRIC's short predicate name."""

    source_uri: str
    predicate: str
    target_uri: str


@dataclass(frozen=True)
class Family:
    """What the two legs found, before any fabric call has been made.

    Deliberately not a `ContextProduct`, not a `GraphView` and not a set of
    envelopes: this module's output is domain data, and the vocabulary layer
    beside it is what turns domain data into fabric state.
    """

    anchor_uri: str
    anchor_lei: str
    #: The identifier every admitted node carries as its observed family
    #: membership. The anchor's LEI, because that is the family's public name
    #: and the same token the request asked in.
    family_id: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    #: LEI -> the attribute row that resolved it. Most admitted nodes are
    #: absent from this mapping, and that absence is the product's debt signal.
    attributes: Mapping[str, Mapping[str, Any]]
    #: The graph leg's own transaction watermark at the moment it was read.
    #: Recorded BESIDE the fabric's snapshot instant and never inside it: it is
    #: the source store's clock, not the fabric's.
    ledger_watermark: str
    #: The depth actually reached, which can be less than the depth requested
    #: when the family is exhausted first. Served in the payload beside the
    #: depth asked for, so a caller can tell "there is no more" from "we
    #: stopped".
    depth_reached: int


class _GraphLeg:
    """A read-only SPARQL client for the family ledger."""

    def __init__(self, *, url: str, ledger: str, client: httpx.Client) -> None:
        self._url = url.rstrip("/")
        self._ledger = ledger
        self._client = client

    def query(self, body: str) -> list[Mapping[str, Any]]:
        """One SPARQL SELECT, with the ledger named explicitly.

        `FROM <ledger>` precedes `WHERE` in every query this leg issues, and it
        is never omitted: the server answers HTTP 400 without it, and a
        defaulted ledger would be a store nobody named.
        """
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body.encode("utf-8"),
        )
        response.raise_for_status()
        bindings: list[Mapping[str, Any]] = response.json()["results"]["bindings"]
        return bindings

    def watermark(self) -> str:
        """The ledger's transaction index `t`, as the store itself reports it.

        Read from the server's ledger listing and matched on this ledger's own
        name and branch, because the store keys the two separately: a
        `name:branch` string is one identifier to this deployment and two
        fields to Fluree.

        **Reported as `unreported` rather than as a number this code invented**
        when the listing does not carry this ledger. A fabricated watermark
        would be worse than an absent one: it would put a specific, checkable,
        false claim about the source's state into the served payload.
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return "unreported"
        # `name:branch`, or a BARE NAME whose branch is `main`. Fluree keys the
        # two separately, and a bare `fibo-v2` partitions to an EMPTY branch —
        # which matches no listing entry and silently reports `unreported`
        # against a ledger that is right there. Seeded test ledgers carry an
        # explicit `ccf:cp04-…`, so the defect only appeared against the
        # curated estate, which is the value this example's README tells a
        # reader to export (`CP06-F-01`, `D-IMPL-322`).
        name, separator, branch = self._ledger.partition(":")
        if not separator:
            branch = "main"
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch") == branch:
                return str(entry["t"])
        return "unreported"

    @property
    def ledger(self) -> str:
        return self._ledger


def _values(terms: Sequence[str]) -> str:
    """A SPARQL `VALUES` list of IRIs — the batching primitive of the walk."""
    return " ".join(f"<{term}>" for term in terms)


#: What may stand between a SPARQL string literal's quotes WITHOUT an escape.
#: SPARQL 1.1 `STRING_LITERAL2` excludes `"`, `\`, LF and CR; this holds the
#: text tighter, to no control character at all. A value outside it is REFUSED,
#: never escaped, so no escape processing — an `ECHAR`, or the `\u` pre-pass
#: SPARQL 1.1 §19.2 applies before parsing — ever reads request text (`EX-01`).
_LITERAL_TEXT = re.compile(r'[^"\\\x00-\x1f\x7f]*')


def _literal(value: str) -> str:
    """`value` as a quoted SPARQL string literal, or refused before any read."""
    if not _LITERAL_TEXT.fullmatch(value):
        raise ValueError(f"{value!r} cannot be placed in a SPARQL string literal")
    return f'"{value}"'


def _walk(
    leg: _GraphLeg, *, anchor_uri: str, depth: int, predicates: Mapping[str, str]
) -> tuple[dict[str, int], list[Edge], int]:
    """Expand the frontier one hop at a time, batched over the whole level.

    Returns the admitted nodes with the depth each was first reached at, every
    edge traversed, and the depth actually reached.

    **A node is admitted once, at the shallowest depth that reaches it.** Later
    hops still record their edges — the tree is a graph and the edges are the
    subject of the product — but they do not re-admit the node, which is also
    what stops a cycle from making the walk non-terminating.
    """
    admitted = {anchor_uri: 0}
    frontier = [anchor_uri]
    edges: list[Edge] = []
    reached = 0

    for hop in range(1, depth + 1):
        if not frontier:
            break
        rows = leg.query(
            f"SELECT ?s ?p ?o FROM <{leg.ledger}> WHERE {{"
            f" VALUES ?s {{ {_values(frontier)} }}"
            f" VALUES ?p {{ {_values(list(predicates))} }}"
            f" ?s ?p ?o }}"
        )
        following: list[str] = []
        for row in rows:
            source_uri = row["s"]["value"]
            target_uri = row["o"]["value"]
            edges.append(
                Edge(
                    source_uri=source_uri,
                    predicate=predicates[row["p"]["value"]],
                    target_uri=target_uri,
                )
            )
            if target_uri not in admitted:
                admitted[target_uri] = hop
                following.append(target_uri)
        if rows:
            reached = hop
        frontier = following

    return admitted, edges, reached


def _details(
    leg: _GraphLeg, *, uris: Sequence[str], vocab: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Class chain, label and LEI for every admitted node, in three batches.

    Three queries rather than one: the ontology chain is multi-valued per node
    and joining it against two single-valued predicates in one pattern returns
    the cross product, which silently multiplies rows. Three narrow reads are
    cheaper than one wide read that has to be de-duplicated afterwards.
    """
    found: dict[str, dict[str, Any]] = {
        uri: {"type_chain": [], "label": None, "lei": None} for uri in uris
    }
    batch = _values(uris)

    for row in leg.query(
        f"SELECT ?s ?t FROM <{leg.ledger}> WHERE {{ VALUES ?s {{ {batch} }}"
        " ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?t }"
    ):
        found[row["s"]["value"]]["type_chain"].append(row["t"]["value"])

    for predicate, field in (
        (vocab["graph_leg"]["label_predicate"], "label"),
        (vocab["graph_leg"]["lei_predicate"], "lei"),
    ):
        for row in leg.query(
            f"SELECT ?s ?v FROM <{leg.ledger}> WHERE {{ VALUES ?s {{ {batch} }}"
            f" ?s <{predicate}> ?v }}"
        ):
            found[row["s"]["value"]][field] = row["v"]["value"]

    return found


def _attributes(
    *, leis: Sequence[str], vocab: Mapping[str, Any], settings: Mapping[str, str]
) -> dict[str, dict[str, Any]]:
    """ONE query for the whole key set — the batched join, not a fan-out.

    Returns only the keys that resolved. An unresolved LEI is absent rather
    than present-and-empty: a row of nulls would be this deployment asserting
    something the source never said, and the whole debt signal depends on the
    difference being visible.
    """
    if not leis:
        return {}
    leg = vocab["attribute_leg"]
    columns = ", ".join(f'"{column}"' for column in leg["columns"])
    statement = (
        f'SELECT {columns} FROM "{settings["schema"]}"'
        f'."{leg["table"]}" WHERE "{leg["key_column"]}" = ANY(%s)'
    )
    with psycopg.connect(settings["dsn"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, (list(leis),))
            rows = cursor.fetchall()
    return {
        row[0]: dict(zip(leg["columns"], row, strict=True))
        for row in rows
    }


def acquire(
    *, anchor_lei: str, depth: int, graph: Mapping[str, str], attributes: Mapping[str, str]
) -> Family:
    """Open both stores, walk one, join the other, and admit what was found.

    Args:
        anchor_lei: The family's anchor, as the caller named it.
        depth: The EFFECTIVE depth — already folded through the class default,
            the declared domain and the graph leg's technical capability by
            `resolve_effective_request`. This function receives a number that
            survived governance and applies no bound of its own; a second
            ceiling here would be a second authority for one value.
        graph: The graph leg's connection settings (``url``, ``ledger``), as
            the paved road resolved them from the environment document.
        attributes: The attribute leg's (``dsn``, ``schema``), likewise. This
            module reads no environment variable itself (`D-IMPL-343`).

    Raises:
        LookupError: the anchor resolves to no node. An unresolvable anchor is
            a refusal, never an empty payload — an empty family is a claim
            about the world, and this one would be a claim about the request.
        ValueError: the anchor holds text a SPARQL string literal cannot carry
            unescaped, refused by ``_literal`` before any store is read.
    """
    vocab = vocabulary()
    predicates: Mapping[str, str] = vocab["graph_leg"]["family_predicates"]

    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        leg = _GraphLeg(url=graph["url"], ledger=graph["ledger"], client=client)

        anchors = leg.query(
            f"SELECT ?s FROM <{leg.ledger}> WHERE {{"
            f" ?s <{vocab['graph_leg']['lei_predicate']}> {_literal(anchor_lei)} }}"
        )
        if not anchors:
            raise LookupError(
                f"no node in ledger {leg.ledger!r} carries LEI {anchor_lei!r}"
            )
        anchor_uri = anchors[0]["s"]["value"]

        admitted, edges, reached = _walk(
            leg, anchor_uri=anchor_uri, depth=depth, predicates=predicates
        )
        details = _details(leg, uris=sorted(admitted), vocab=vocab)
        watermark = leg.watermark()

    nodes = tuple(
        Node(
            uri=uri,
            lei=details[uri]["lei"],
            label=details[uri]["label"],
            type_chain=tuple(sorted(details[uri]["type_chain"])),
            depth=hop,
        )
        for uri, hop in sorted(admitted.items())
    )
    resolved = _attributes(
        leis=[node.lei for node in nodes if node.lei], vocab=vocab, settings=attributes
    )

    return Family(
        anchor_uri=anchor_uri,
        anchor_lei=anchor_lei,
        # Minted at admission, from the anchor the walk actually started at.
        family_id=anchor_lei,
        nodes=nodes,
        edges=tuple(edges),
        attributes=resolved,
        ledger_watermark=watermark,
        depth_reached=reached,
    )
