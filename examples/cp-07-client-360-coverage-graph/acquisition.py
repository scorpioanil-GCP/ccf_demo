"""The two source legs for the coverage graph, and nothing else.

[ADAPT] everything. [MECHANISM] nothing — **this module imports no `ccf`**.

Boundaries are ruled (`D-IMPL-315`): vocabulary, source access and admission.
No binder, no gates, no replay, no serve.

## The bound is a correctness feature, not a convenience

`limit` is applied **inside the read, ordered by recency**. Fetching every
interaction and slicing to 200 in memory satisfies the contract and defeats its
purpose: this is the rung where one client carries 240 interactions and the
fan-out is a genuine operational hazard. The read reports **whether the bound
was reached**, because silent truncation reads as completeness.

## Two namespaces, and the search that missed one

`CP-SPEC-007` §C.2 records the trap in full. Three edges are `ex:`;
`employedBy` is asserted as FIBO **`isEmployedBy`**. `ex:participationIn` and
`ex:participationOf` are a Wave 18 *syndicate* reification and are **not** this
product's. Every IRI is read from `artifacts/source-vocabulary.yaml` rather
than written here.

## Where each fact lives

**Fluree owns the edges; PostgreSQL owns the attributes.** Nothing is
duplicated — a participant's `party_kind` is not on the Fluree edge at all, it
is the subject URI's prefix (`ex:person-*` / `ex:banker-*`). Single-writer
holds on both sides.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

HERE = Path(__file__).parent
READ_TIMEOUT_SECONDS = 180


def _document(path: Path) -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed


def vocabulary() -> Mapping[str, Any]:
    return _document(HERE / "artifacts" / "source-vocabulary.yaml")["declaration"]


def _setting(source: str, name: str) -> str:
    declared = _document(HERE / "backends.yaml")["declaration"]["sources"]
    setting = declared[source]["settings"][name]
    value = os.environ.get(setting["from_env"])
    if not value:
        raise RuntimeError(f"{setting['from_env']} is unset. {setting['remedy'].strip()}")
    return value


@dataclass(frozen=True)
class Person:
    person_key: str
    display_name: str | None
    role: str | None
    officer_title: str | None
    appointment_date: str | None


@dataclass(frozen=True)
class Banker:
    banker_id: str
    full_name: str | None
    role: str | None
    seniority: str | None
    desk: str | None
    is_primary: bool


@dataclass(frozen=True)
class Interaction:
    interaction_id: str
    interaction_type: str | None
    interaction_date: str | None
    channel: str | None
    subject: str | None
    need_to_know: bool
    mnpi_bearing: bool
    deal_id: str | None
    #: (party_kind, party_key) per participant, from the attribute leg.
    participants: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Deal:
    deal_id: str
    deal_type: str | None
    stage: str | None
    opened_date: str | None
    mnpi_bearing: bool


@dataclass(frozen=True)
class Coverage:
    """What the two legs found, before any fabric call."""

    lei: str
    client_name: str | None
    family: tuple[str, ...]
    people: tuple[Person, ...]
    bankers: tuple[Banker, ...]
    interactions: tuple[Interaction, ...]
    deals: tuple[Deal, ...]
    #: The graph edges the walk admitted: (subject_ref, predicate, object_ref).
    edges: tuple[tuple[str, str, str], ...]
    weights: Mapping[str, Any]
    ledger_watermark: str

    #: LEI -> the graph's own local node id for that client. **The edge
    #: endpoints use THESE, never the LEI** — `JJAX4X60DE65EYFOTY73` is the
    #: node `SuburbanPropanePartnersLP`. Carried out of acquisition because
    #: this is where it was resolved; deriving it again downstream would make
    #: a second authority for one identity.
    client_nodes: Mapping[str, str]
    #: Whether `limit` was reached. The payload MUST disclose this — a truncated
    #: roster that did not say so reads as a complete one.
    truncated: bool
    interactions_available: int
    #: Interactions the policy envelope excluded before any of this was walked.
    withheld_need_to_know: int = 0
    withheld_mnpi: int = 0
    unresolved_participants: tuple[str, ...] = field(default_factory=tuple)


def nothing_acquired(lei: str) -> Coverage:
    """What a read that was never taken returns.

    Not an empty answer — **no answer**. Governance refused the question before
    acquisition ran, so there is nothing to report and nothing was paid for. The
    governed resolver issues the refusal moments later; this value only has to
    carry the anchor far enough to get there.
    """
    return Coverage(
        lei=lei, client_name=None, family=(), people=(), bankers=(),
        interactions=(), deals=(), edges=(), weights={},
        ledger_watermark="unread", client_nodes={}, truncated=False,
        interactions_available=0)


class _GraphLeg:
    def __init__(self, *, url: str, ledger: str, client: httpx.Client) -> None:
        self._url, self._ledger, self._client = url.rstrip("/"), ledger, client

    @property
    def ledger(self) -> str:
        return self._ledger

    def query(self, body: str) -> list[Mapping[str, Any]]:
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body.encode("utf-8"))
        response.raise_for_status()
        rows: list[Mapping[str, Any]] = response.json()["results"]["bindings"]
        return rows

    def watermark(self) -> str:
        """The ledger's `t`, or `unreported` — never a number this code invented.

        A bare ledger name carries branch `main`; Fluree keys name and branch
        separately (`D-IMPL-322`).
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return "unreported"
        name, separator, branch = self._ledger.partition(":")
        if not separator:
            branch = "main"
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch") == branch:
                return str(entry["t"])
        return "unreported"


def _local(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _values(terms: Sequence[str]) -> str:
    return " ".join(f"<{t}>" for t in terms)


def _client_nodes(leg: _GraphLeg, vocab: Mapping[str, Any],
                  leis: Sequence[str]) -> dict[str, str]:
    """LEI -> the graph's own node URI for that client.

    **A client is NOT addressed by its LEI in this ledger.** It is a
    name-derived URI — `JJAX4X60DE65EYFOTY73` is
    `http://example.org/fibo/SuburbanPropanePartnersLP`. Walking from the LEI
    directly returns nothing, silently, and the product then serves a coverage
    graph with no graph in it. Resolved through `ex:lei` rather than assumed.
    """
    quoted = " ".join(f'"{lei}"' for lei in leis)
    return {
        b["lei"]["value"]: b["s"]["value"]
        for b in leg.query(
            f'SELECT ?s ?lei FROM <{leg.ledger}> WHERE {{'
            f' VALUES ?lei {{ {quoted} }}'
            f' ?s <{vocab["graph_leg"]["lei"]}> ?lei }}')
    }


def _walk_graph(leg: _GraphLeg, vocab: Mapping[str, Any],
                anchors: Sequence[str]) -> list[tuple[str, str, str]]:
    """The coverage edges touching this client (or family), batched per edge type.

    One query per declared edge type rather than one per node: four queries
    regardless of graph size. At this fan-out the N+1 pattern is not a
    performance note — it is the difference between meeting and missing the
    interactive target §7.6 sets.
    """
    edges = vocab["graph_leg"]["edges"]
    uris = list(anchors)          # already node URIs, resolved by `_client_nodes`
    found: list[tuple[str, str, str]] = []
    if not uris:
        return found

    # Edges pointing AT the client: who covers it, who is employed by it.
    for short in ("coversClient", "employedBy"):
        for b in leg.query(
            f'SELECT ?s ?o FROM <{leg.ledger}> WHERE {{'
            f' VALUES ?o {{ {_values(uris)} }} ?s <{edges[short]["iri"]}> ?o }}'
        ):
            found.append((_local(b["s"]["value"]), short, _local(b["o"]["value"])))
    return found


def _walk_participation(leg: _GraphLeg, vocab: Mapping[str, Any],
                        interaction_ids: Sequence[str]) -> list[tuple[str, str, str]]:
    """Who took part in the admitted interactions — ONE batched query.

    Runs AFTER the interaction set is bounded, never before: walking
    participation first would fan out over every interaction in the estate and
    then discard most of it, which is the shape this product exists to refuse.
    """
    if not interaction_ids:
        return []
    edges = vocab["graph_leg"]["edges"]
    # Node ids carry a KIND PREFIX in this ledger: an interaction `INT-00000`
    # is the node `interaction-INT-00000`. The prefix is declared beside the
    # edge rather than written here.
    prefix = vocab["graph_leg"]["node_prefixes"]["interaction"]
    uris = [f"http://example.org/fibo/{prefix}{i}" for i in interaction_ids]
    return [
        (_local(b["s"]["value"]), "participatedIn", _local(b["o"]["value"]))
        for b in leg.query(
            f'SELECT ?s ?o FROM <{leg.ledger}> WHERE {{'
            f' VALUES ?o {{ {_values(uris)} }}'
            f' ?s <{edges["participatedIn"]["iri"]}> ?o }}')
    ]


def _walk_deals(leg: _GraphLeg, vocab: Mapping[str, Any],
                interaction_ids: Sequence[str]) -> list[tuple[str, str, str]]:
    """Which deals the admitted interactions concern — ONE batched query.

    §C's fourth edge. Walked from the BOUNDED interaction set for the same
    reason participation is: starting from deals would fan out over the estate
    and then discard most of it.
    """
    if not interaction_ids:
        return []
    edges = vocab["graph_leg"]["edges"]
    prefix = vocab["graph_leg"]["node_prefixes"]["interaction"]
    uris = [f"http://example.org/fibo/{prefix}{i}" for i in interaction_ids]
    return [
        (_local(b["s"]["value"]), "relatedToDeal", _local(b["o"]["value"]))
        for b in leg.query(
            f'SELECT ?s ?o FROM <{leg.ledger}> WHERE {{'
            f' VALUES ?s {{ {_values(uris)} }}'
            f' ?s <{edges["relatedToDeal"]["iri"]}> ?o }}')
    ]


def _bounded_interactions(cur: Any, schema: str, vocab: Mapping[str, Any], *,
                          leis: Sequence[str], since: str, limit: int,
                          include_need_to_know: bool) -> tuple[
                              list[Interaction], bool, int, int, int]:
    """Interactions within the window, ORDERED BY RECENCY, `limit` applied IN the read.

    Returns the admitted set, whether the bound was reached, how many were
    available, and how many the policy envelope withheld.

    **The policy exclusion happens HERE, in the read**, not after it: an
    interaction the principal may not see is never materialized, so no
    participation edge to it is ever walked. §D step 2 — *"the difference is
    invisible in the output and fundamental to the architecture."*
    """
    leg = vocab["attribute_leg"]
    table = leg["interaction_table"]
    clause = "" if include_need_to_know else " AND NOT need_to_know"

    cur.execute(
        f'SELECT count(*), count(*) FILTER (WHERE need_to_know),'
        f' count(*) FILTER (WHERE mnpi_bearing)'
        f' FROM "{schema}".{table} WHERE lei = ANY(%s) AND interaction_date >= %s',
        (list(leis), since))
    available, need_to_know, mnpi = cur.fetchone()

    cur.execute(
        f'SELECT interaction_id, interaction_type, interaction_date, channel,'
        f' subject, need_to_know, mnpi_bearing, deal_id'
        f' FROM "{schema}".{table}'
        f' WHERE lei = ANY(%s) AND interaction_date >= %s{clause}'
        # ORDERED BY RECENCY AND BOUNDED IN THE READ. The tie-break on id keeps
        # two runs of one question identical when dates collide.
        f' ORDER BY interaction_date DESC, interaction_id'
        f' LIMIT %s',
        (list(leis), since, limit))
    rows = cur.fetchall()

    admitted = [
        Interaction(
            interaction_id=r[0], interaction_type=r[1],
            interaction_date=r[2].isoformat() if r[2] else None,
            channel=r[3], subject=r[4], need_to_know=bool(r[5]),
            mnpi_bearing=bool(r[6]), deal_id=r[7], participants=())
        for r in rows
    ]
    admissible = available - (0 if include_need_to_know else need_to_know)
    return admitted, len(admitted) < admissible, available, need_to_know, mnpi


def _participant_attributes(cur: Any, schema: str, vocab: Mapping[str, Any],
                            interaction_ids: Sequence[str]) -> dict[
                                str, list[tuple[str, str]]]:
    """The attribute half of participation — ONE batched query.

    The EDGE is Fluree's; `party_kind` and `provenance` are PostgreSQL's, and
    nothing is duplicated across the two.
    """
    if not interaction_ids:
        return {}
    table = vocab["attribute_leg"]["participant_table"]
    cur.execute(
        f'SELECT interaction_id, party_kind, party_key FROM "{schema}".{table}'
        f' WHERE interaction_id = ANY(%s)', (list(interaction_ids),))
    out: dict[str, list[tuple[str, str]]] = {}
    for interaction_id, kind, key in cur.fetchall():
        out.setdefault(interaction_id, []).append((kind, key))
    return out


def acquire(*, lei: str, since: str, limit: int, include_family: bool,
            include_need_to_know: bool) -> Coverage:
    """Open both stores and read this client's coverage graph.

    Every bound arrives already folded through class defaults and policy by
    `resolve_effective_request`; this function applies none of its own, because
    a second bound would be a second authority for one value.
    """
    vocab = vocabulary()
    schema = _setting("coverage_attributes", "schema")
    leg_attr = vocab["attribute_leg"]

    with psycopg.connect(_setting("coverage_attributes", "dsn")) as db, db.cursor() as cur:
        cur.execute(f'SELECT legal_name FROM "{schema}".legal_entity WHERE lei = %s', (lei,))
        row = cur.fetchone()
        if row is None:
            raise LookupError(
                f"client {lei!r} resolves to no row in {schema}.legal_entity;"
                " an unknown client is a claim about the request, not the world")
        client_name = row[0]

        family = [lei]
        if include_family:
            cur.execute(
                f'SELECT DISTINCT child_lei FROM "{schema}".corporate_ownership_record'
                f' WHERE parent_lei = %s', (lei,))
            family += [r[0] for r in cur.fetchall() if r[0]]

        interactions, truncated, available, withheld_ntk, mnpi = _bounded_interactions(
            cur, schema, vocab, leis=family, since=since, limit=limit,
            include_need_to_know=include_need_to_know)

        ids = [i.interaction_id for i in interactions]
        participants = _participant_attributes(cur, schema, vocab, ids)

        cur.execute(
            f'SELECT DISTINCT p.person_key, p.display_name, r.role, r.officer_title,'
            f' r.appointment_date FROM "{schema}".{leg_attr["person_role_table"]} r'
            f' JOIN "{schema}".{leg_attr["person_table"]} p USING (person_key)'
            f' WHERE r.lei = ANY(%s)', (family,))
        people = [Person(person_key=r[0], display_name=r[1], role=r[2],
                         officer_title=r[3],
                         appointment_date=r[4].isoformat() if r[4] else None)
                  for r in cur.fetchall()]

        cur.execute(
            f'SELECT b.banker_id, b.full_name, b.role, b.seniority, b.desk,'
            f' bool_or(c.is_primary) FROM "{schema}".{leg_attr["coverage_table"]} c'
            f' JOIN "{schema}".{leg_attr["banker_table"]} b USING (banker_id)'
            f' WHERE c.lei = ANY(%s) GROUP BY 1,2,3,4,5', (family,))
        bankers = [Banker(banker_id=r[0], full_name=r[1], role=r[2], seniority=r[3],
                          desk=r[4], is_primary=bool(r[5])) for r in cur.fetchall()]

        cur.execute(
            f'SELECT weight_name, weight_value FROM "{schema}".{leg_attr["weight_table"]}')
        weights = {n: v for n, v in cur.fetchall()}

    deal_edges: list[tuple[str, str, str]] = []
    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        graph = _GraphLeg(url=_setting("coverage_graph", "url"),
                          ledger=_setting("coverage_graph", "ledger"), client=client)
        nodes = _client_nodes(graph, vocab, family)
        edges = _walk_graph(graph, vocab, list(nodes.values()))
        edges += _walk_participation(graph, vocab, ids)
        deal_edges = _walk_deals(graph, vocab, ids)
        edges += deal_edges
        watermark = graph.watermark()

    # THE ATTRIBUTES FOR THE DEALS THE WALK REACHED, and only those. A second
    # connection rather than one more query inside the first block, because the
    # deal ids are not known until the graph leg has been walked — and the graph
    # leg cannot be walked until the interaction set is bounded.
    prefix = vocab["graph_leg"]["node_prefixes"]["deal"]
    reached = sorted({o[len(prefix):] for _, _, o in deal_edges if o.startswith(prefix)})
    deals: list[Deal] = []
    if reached:
        with psycopg.connect(_setting("coverage_attributes", "dsn")) as db, db.cursor() as cur:
            cur.execute(
                f'SELECT deal_id, deal_type, stage, opened_date, mnpi_bearing'
                f' FROM "{schema}".{leg_attr["deal_table"]} WHERE deal_id = ANY(%s)',
                (reached,))
            deals = [Deal(deal_id=r[0], deal_type=r[1], stage=r[2],
                          opened_date=r[3].isoformat() if r[3] else None,
                          mnpi_bearing=bool(r[4])) for r in cur.fetchall()]

    known = {p.person_key for p in people} | {b.banker_id for b in bankers}
    unresolved = sorted({
        key for parts in participants.values() for _, key in parts
        if key not in known})

    return Coverage(
        lei=lei, client_name=client_name, family=tuple(family),
        people=tuple(sorted(people, key=lambda p: p.person_key)),
        bankers=tuple(sorted(bankers, key=lambda b: b.banker_id)),
        deals=tuple(sorted(deals, key=lambda d: d.deal_id)),
        interactions=tuple(
            Interaction(**{**i.__dict__,
                           "participants": tuple(sorted(participants.get(i.interaction_id, ())))})
            for i in interactions),
        edges=tuple(sorted(set(edges))), weights=weights,
        ledger_watermark=watermark,
        client_nodes={lei: _local(uri) for lei, uri in nodes.items()}, truncated=truncated,
        interactions_available=available, withheld_need_to_know=withheld_ntk,
        withheld_mnpi=mnpi, unresolved_participants=tuple(unresolved))
