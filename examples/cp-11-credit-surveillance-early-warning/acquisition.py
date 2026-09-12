"""The two source legs, bounded at the decision instant.

[ADAPT] everything here. [MECHANISM] nothing.

**PostgreSQL carries the clock; Fluree carries the chain.** Measured at Gate 1
and it shapes this module: a Fluree `WarningSignal` node has `rdf:type`,
`rdfs:label`, `provenance`, `signalAbout`, `triggeredBy` and `supersededBy` —
and **no timestamp of any kind**. The date appears only inside the label
*string*. So every instant in this product comes from `signal_event.observed_at`
in PostgreSQL, and `CP11-F-07` forbids parsing one out of a label. A label is
prose, not a clock.

The two legs join on `signal_id`: the PostgreSQL primary key is the local part
of the Fluree IRI (`sig-8k-02a95d9e9460`). Verified at Gate 1.

Reads only. Nothing here writes to either store.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
import yaml

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"

#: The Fluree term namespace this estate uses. Read from the artifact, never
#: spelled in code (CLAUDE.md §6.4).
FIBO = "http://example.org/fibo/"


class UnknownObligor(RuntimeError):
    """The estate holds no such obligor.

    A **request error**, and distinct from *"this obligor produced no signal in
    the delta"*, which is a fact about the world and serves with a `no-change`
    finding (`EWS-G11`, `EWS-G17`). Collapsing the two tells a caller to fix
    their input when the input was right.
    """


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. This example reads a live estate; see the"
            " README's Run-it section for the read-only role it needs"
        )
    return value


def sector_of(sic: str | None, terms: Mapping[str, Any]) -> str:
    """The SIC DIVISION a four-digit SIC code falls in (`CP11-F-09`).

    `signal_weight` keys on the nine standard SIC division names;
    `legal_entity` carries a specific code and description. Measured at Gate 2:
    **zero of the 50 anchors' `sic_description` values match a sector name**, so
    without this resolution every obligor falls to `Unclassified` and 36 of the
    table's 45 rows can never be read — the whole sector dimension inert while
    looking configured.

    The boundaries are the published SIC divisions and live in the artifact,
    never here. An absent or unmappable code returns the declared
    `Unclassified`, which is a real row in the weight table rather than a skip.
    """
    fallback = str(terms["unclassified_sector"])
    if sic is None:
        return fallback
    try:
        code = int(str(sic).strip())
    except ValueError:
        return fallback
    for division in terms["sic_divisions"]:
        if int(division["from"]) <= code <= int(division["to"]):
            return str(division["sector"])
    return fallback


def vocabulary() -> Mapping[str, Any]:
    """The source terms this deployment reads, named once in an artifact."""
    document: Mapping[str, Any] = yaml.safe_load(
        VOCABULARY.read_text(encoding="utf-8")
    )
    return document["declaration"]


@dataclass(frozen=True)
class Signal:
    """One dated signal, as the source recorded it.

    ``observed_at`` is the **source's own observation date** — when the filing
    was made, the notice published, the mention seen. It is never an ingestion
    instant, and it is what the delta bound and every decay curve read.
    """

    signal_id: str
    lei: str
    signal_type: str
    observed_at: date
    severity: Decimal
    source_ref: Mapping[str, Any]
    provenance: str

    @property
    def item(self) -> str | None:
        """The 8-K item, for an `8k_event`. ``None`` for every other class."""
        value = self.source_ref.get("item")
        return None if value is None else str(value)


@dataclass(frozen=True)
class Obligor:
    lei: str
    legal_name: str
    #: The SIC DIVISION, which is what `signal_weight` keys on — never the
    #: specific `sic_description` (`CP11-F-09`).
    sector: str
    sic: str | None


@dataclass(frozen=True)
class Estate:
    """One obligor's signal evidence over one delta window."""

    obligor: Obligor
    #: Every signal in `(since, asked_at]`, oldest first.
    signals: tuple[Signal, ...]
    #: The signal ids Fluree reports as CURRENT — not superseded by a later
    #: one. Only `8k_event` participates; measured at Gate 1.
    current_signal_ids: frozenset[str]
    #: Every signal id Fluree mirrors at all, so *"not current"* can be told
    #: from *"never in the chain"*. A class with no chain is not superseded by
    #: silence.
    chained_signal_ids: frozenset[str]
    #: The obligor's prior-observation anchor — the delta's default left edge.
    prior_observation: date | None
    #: The weights and decay, by `(signal_type, sector)`.
    weights: Mapping[tuple[str, str], tuple[Decimal, int | None]]
    #: The escalation bands by intent, lowest first.
    thresholds: Mapping[str, Decimal]
    #: How many WARN matches for this obligor were too ambiguous to consume.
    ambiguous_warn_matches: int
    #: The window actually read.
    window_from: date
    window_to: date


class _Relational:
    """PostgreSQL. Reads only."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn = dsn
        self._schema = schema

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(f"SET search_path TO {self._schema}")
            return connection.execute(sql, params).fetchall()


class _Graph:
    """Fluree, over SPARQL. Reads only."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url = url.rstrip("/")
        self._ledger = ledger

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


def acquire(
    *, anchor_lei: str, asked_at: datetime, since: date | None, window_days: int
) -> Estate:
    """Read both legs for one obligor over one delta window.

    The window's right edge is the decision instant. Its left edge is ``since``
    when the caller supplied one, otherwise the obligor's prior-observation
    anchor, otherwise ``window_days`` back — **the delta needs a prior, and a
    fixed lookback is the last resort rather than the default** (`CP11-F-03`
    records that every anchor in this estate carries the same seeded date).

    Nothing later than ``asked_at`` is read: a filing made after the decision
    instant is not yet knowable (`EWS-G10`).
    """
    relational = _Relational(
        dsn=_setting("CCF_CP_11_POSTGRES_DSN"),
        schema=_setting("CCF_CP_11_POSTGRES_SCHEMA"),
    )
    graph = _Graph(
        url=_setting("CCF_CP_11_FLUREE_URL"),
        ledger=_setting("CCF_CP_11_FLUREE_LEDGER"),
    )
    terms = vocabulary()
    window_to = asked_at.date()

    found = relational.rows(
        "SELECT lei, legal_name, sic FROM legal_entity WHERE lei = %s",
        (anchor_lei,),
    )
    if not found:
        raise UnknownObligor(
            f"obligor {anchor_lei!r} is not available (404); this product"
            " surveils obligors the estate holds and fails closed rather than"
            " returning an empty delta"
        )
    obligor = Obligor(
        lei=found[0][0],
        legal_name=found[0][1],
        sector=sector_of(found[0][2], terms),
        sic=found[0][2],
    )

    prior = _prior_observation(graph, terms, lei=anchor_lei)
    window_from = since or prior or (
        date.fromordinal(window_to.toordinal() - window_days)
    )

    signals = tuple(
        Signal(
            signal_id=row[0],
            lei=row[1],
            signal_type=row[2],
            observed_at=row[3],
            severity=Decimal(str(row[4])),
            source_ref=row[5] or {},
            provenance=row[6],
        )
        for row in relational.rows(
            "SELECT signal_id, lei, signal_type, observed_at, severity,"
            " source_ref, provenance FROM signal_event"
            " WHERE lei = %s AND observed_at > %s AND observed_at <= %s"
            " ORDER BY observed_at, signal_id",
            (anchor_lei, window_from, window_to),
        )
    )

    current, chained = _supersession(graph, terms, lei=anchor_lei)
    return Estate(
        obligor=obligor,
        signals=signals,
        current_signal_ids=current,
        chained_signal_ids=chained,
        prior_observation=prior,
        weights=_weights(relational),
        thresholds=_thresholds(relational),
        ambiguous_warn_matches=_ambiguous_warn_matches(relational, lei=anchor_lei),
        window_from=window_from,
        window_to=window_to,
    )


def _prior_observation(
    graph: _Graph, terms: Mapping[str, Any], *, lei: str
) -> date | None:
    """The obligor's delta anchor, from its `PriorObservation` node."""
    rows = graph.select(
        f"SELECT ?v FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['prior_observation_class']}> ."
        f" ?s <{terms['signal_about']}> ?o ."
        f" ?o <{terms['lei']}> {json.dumps(lei)} ."
        f" ?s <{terms['valid_from']}> ?v }}"
    )
    if not rows:
        return None
    return date.fromisoformat(str(rows[0]["v"])[:10])


def _supersession(
    graph: _Graph, terms: Mapping[str, Any], *, lei: str
) -> tuple[frozenset[str], frozenset[str]]:
    """``(current, chained)`` signal ids for this obligor.

    **Two sets, not one.** ``chained`` is every signal Fluree mirrors;
    ``current`` is the subset carrying no ``supersededBy``. A signal absent from
    ``chained`` is in no chain at all — measured, only `8k_event` is — and must
    not be read as superseded. Silence is not supersession (`EWS-G08`).
    """
    rows = graph.select(
        f"SELECT ?s FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['warning_signal_class']}> ."
        f" ?s <{terms['signal_about']}> ?o ."
        f" ?o <{terms['lei']}> {json.dumps(lei)} }}"
    )
    chained = frozenset(str(row["s"]).rsplit("/", 1)[-1] for row in rows)
    rows = graph.select(
        f"SELECT ?s FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['warning_signal_class']}> ."
        f" ?s <{terms['signal_about']}> ?o ."
        f" ?o <{terms['lei']}> {json.dumps(lei)} ."
        f" FILTER NOT EXISTS {{ ?s <{terms['superseded_by']}> ?x }} }}"
    )
    current = frozenset(str(row["s"]).rsplit("/", 1)[-1] for row in rows)
    return current, chained


def _weights(
    relational: _Relational,
) -> Mapping[tuple[str, str], tuple[Decimal, int | None]]:
    """The λ_c table the estate already carries: weight and decay per class."""
    return {
        (row[0], row[1]): (Decimal(str(row[2])), row[3])
        for row in relational.rows(
            "SELECT signal_type, sector, weight, decay_days FROM signal_weight"
        )
    }


def _thresholds(relational: _Relational) -> Mapping[str, Decimal]:
    """The escalation bands, by intent."""
    return {
        row[0]: Decimal(str(row[1]))
        for row in relational.rows(
            "SELECT intent, threshold_score FROM escalation_threshold"
            " WHERE kind = 'escalation' AND threshold_score IS NOT NULL"
        )
    }


def _ambiguous_warn_matches(relational: _Relational, *, lei: str) -> int:
    """How many WARN matches for this obligor were too ambiguous to consume.

    Published rather than dropped (`EWS-G14`). Measured at Gate 1: **32 of the
    estate's 36 matches are ambiguous and wrong** — TransDigm to Transdev,
    B&G Foods to US Foods, SP Plus to Lamps Plus, all at score ≈0.71. Only the
    4 resolved ones became signals. A reader is told how many were withheld and
    why; a silent drop would look identical to there being none.
    """
    rows = relational.rows(
        "SELECT count(*) FROM warn_match WHERE lei = %s AND verdict <> 'resolved'",
        (lei,),
    )
    return int(rows[0][0]) if rows else 0
