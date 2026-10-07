"""The two source legs, bounded at the decision instant.

[ADAPT] everything here. [MECHANISM] nothing.

**PostgreSQL carries the values; Fluree carries the instants.**
`system_trade_record` has no timestamp column at all — measured — so every
observation instant in this product comes from the ledger's
`SystemObservation.systemObservedAt`, and the two legs join on the IRI
`obs-<trade_id>-<system>-<amendment_seq>`.

## The clock offset, and what it is not

Each system carries a recorded `clockOffsetSeconds` — trading `0`, settlement
`+47`, risk `−112`. Correcting a recorded instant by it recovers the instant the
system *actually* observed at.

**That correction is PRODUCT CONTEXT and not an SDK temporal axis** (Dave,
2026-09-12). The corrected instant is used to compare two systems and for nothing
else: it reaches no ``valid_from``, no ``observed_at``, no invalidation boundary
and no Context Debt term. What the λ_c table ages against is the instant the
SOURCE RECORDED (`D-IMPL-331`), and a corrected instant on that path would make
the fabric's freshness figure a function of this product's own alignment model.

Reads only. Nothing here writes to either store.
"""

from __future__ import annotations

import bisect
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
from psycopg.sql import SQL, Identifier

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"
PIP_SCALE = HERE / "artifacts" / "pip-scale.yaml"

#: The two comparison instants the product offers (§B.2a). `amendment-0` is the
#: state in which a break actually occurred; `latest` is what a conventional
#: reconciliation sees. The product never silently substitutes one for the other.
COMPARE_AT = ("amendment-0", "latest")


class UnknownTrade(RuntimeError):
    """The estate holds no such trade.

    A **request error**, distinct from *"this trade has no break"*, which is a
    fact about the world and serves with a `no-break` verdict (`FXR-G20`).
    """


class PipScaleUndeclared(RuntimeError):
    """The pip artifact names no scale for this pair.

    **Refused rather than defaulted.** Defaulting to `0.0001` is exactly how a
    JPY-quoted pair comes to report a variance a hundred times too small and
    passes every materiality threshold (`FXR-G26`).
    """


class PipScaleDisagrees(RuntimeError):
    """The declaration and the estate's own pip table disagree.

    The declaration is the authority and the estate is the corroboration, so a
    disagreement is a refusal rather than a silent preference for either.
    """


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. This example reads a live estate; see the"
            " README's Run-it section for the read-only role it needs"
        )
    return value


def vocabulary() -> Mapping[str, Any]:
    """The source terms this deployment reads, named once in an artifact."""
    document: Mapping[str, Any] = yaml.safe_load(
        VOCABULARY.read_text(encoding="utf-8")
    )
    return document["declaration"]


def pip_scale() -> Mapping[str, Decimal]:
    """The declared pip scale. An assertion with a version, not a constant."""
    document = yaml.safe_load(PIP_SCALE.read_text(encoding="utf-8"))
    return {
        str(pair): Decimal(str(value))
        for pair, value in document["declaration"]["pips"].items()
    }


@dataclass(frozen=True)
class Observation:
    """One system's value for one trade at one amendment.

    Carries **three instants and never conflates them** (`FXR-G05`):
    ``recorded_at`` is what the system wrote, ``clock_offset_seconds`` is the
    correction this product applies, and ``corrected_at`` is the result. The
    fabric sees only the first.
    """

    trade_id: str
    system: str
    amendment_seq: int
    value_rate: Decimal
    recorded_at: datetime
    clock_offset_seconds: int

    @property
    def corrected_at(self) -> datetime:
        """The instant this system actually observed at.

        **Product context only.** Never a `valid_from`, never an `observed_at`,
        never a decay basis (`FXR-G24`).
        """
        return self.recorded_at - timedelta(seconds=self.clock_offset_seconds)


@dataclass(frozen=True)
class Trade:
    trade_id: str
    pair: str
    execution_ts: datetime
    value_date: date
    #: A BAND, never a number. Part 43 caps large notionals for anonymity, and
    #: this product reconstructs nothing from it (`FXR-G17`).
    notional_band: str
    counterparty_lei: str


@dataclass(frozen=True)
class Tick:
    obs_ts: datetime
    rate: Decimal


@dataclass(frozen=True)
class Estate:
    """What one reconciliation needs."""

    trades: tuple[Trade, ...]
    #: Every observation, by `(trade_id, system)`, oldest amendment first.
    observations: Mapping[tuple[str, str], tuple[Observation, ...]]
    #: The 5-minute rate series per pair, ascending.
    ticks: Mapping[str, tuple[Tick, ...]]
    #: The declared pip scale, corroborated against the estate's own table.
    pips: Mapping[str, Decimal]
    #: The materiality threshold in pips, by intent.
    thresholds: Mapping[str, Decimal]
    #: The designated break sample — NEVER the population (`CP12-F-07`).
    designated: Mapping[str, str]
    #: The comparison instant in force, and the `as_of` that bounded the read.
    compare_at: str
    as_of: datetime
    #: The median spacing of the tick series, in seconds. A decomposition across
    #: an interval shorter than this is NOT EVALUABLE (`FXR-G25`).
    tick_spacing_seconds: int

    def pip(self, pair: str) -> Decimal:
        try:
            return self.pips[pair]
        except KeyError:
            raise PipScaleUndeclared(
                f"the pip artifact declares no scale for {pair!r}; refused"
                " rather than defaulted, because defaulting to 0.0001 makes a"
                " JPY-quoted variance read a hundred times too small"
            ) from None

    def at(self, trade_id: str, system: str) -> Observation | None:
        """The observation this comparison instant selects for one system.

        ``amendment-0`` takes the first; ``latest`` takes the newest at or
        before ``as_of``. **The choice is the caller's and is never made here
        on their behalf** (§B.2a).
        """
        series = self.observations.get((trade_id, system))
        if not series:
            return None
        if self.compare_at == "amendment-0":
            return series[0]
        eligible = [o for o in series if o.recorded_at <= self.as_of]
        return eligible[-1] if eligible else None

    def tick_at(self, pair: str, when: datetime) -> Tick | None:
        """The last tick at or before ``when``. Never interpolated."""
        series = self.ticks.get(pair) or ()
        index = bisect.bisect_right([t.obs_ts for t in series], when) - 1
        return series[index] if index >= 0 else None


class _Relational:
    """PostgreSQL. Reads only."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
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


def acquire(
    *, trade_ids: Sequence[str], asked_at: datetime, compare_at: str,
) -> Estate:
    """Read both legs for a trade set, bounded at the decision instant.

    Nothing recorded after ``asked_at`` is admitted: a system observation the
    fabric could not have known about is not evidence (`FXR-G03`).
    """
    if compare_at not in COMPARE_AT:
        raise ValueError(
            f"compare_at must be one of {COMPARE_AT}, not {compare_at!r};"
            " the comparison instant is an explicit axis and has no fallback"
        )
    relational = _Relational(
        dsn=_setting("CCF_CP_12_POSTGRES_DSN"),
        schema=_setting("CCF_CP_12_POSTGRES_SCHEMA"),
    )
    graph = _Graph(
        url=_setting("CCF_CP_12_FLUREE_URL"),
        ledger=_setting("CCF_CP_12_FLUREE_LEDGER"),
    )
    terms = vocabulary()

    found = relational.rows(
        "SELECT trade_id, pair, execution_ts, value_date, notional_band,"
        " counterparty_lei FROM fx_trade WHERE trade_id = ANY(%s)"
        " ORDER BY trade_id",
        (list(trade_ids),),
    )
    missing = set(trade_ids) - {row[0] for row in found}
    if missing:
        raise UnknownTrade(
            f"trade(s) {sorted(missing)!r} are not available (404); this product"
            " reconciles trades the estate holds and fails closed rather than"
            " returning an empty reconciliation"
        )
    trades = tuple(
        Trade(trade_id=r[0], pair=r[1], execution_ts=r[2], value_date=r[3],
              notional_band=r[4], counterparty_lei=r[5])
        for r in found
    )
    pairs = sorted({t.pair for t in trades})

    offsets = _clock_offsets(graph, terms)
    instants = _observation_instants(graph, terms, trade_ids=[t.trade_id for t in trades])

    observations: dict[tuple[str, str], list[Observation]] = {}
    for row in relational.rows(
        "SELECT trade_id, system_name, amendment_seq, value_rate"
        " FROM system_trade_record WHERE trade_id = ANY(%s)"
        " ORDER BY trade_id, system_name, amendment_seq",
        ([t.trade_id for t in trades],),
    ):
        key = (row[0], row[1], int(row[2]))
        recorded = instants.get(key)
        if recorded is None or recorded > asked_at:
            # NOT YET KNOWABLE, or carrying no instant at all. Excluded rather
            # than given a substitute — the whole product rests on the instant.
            continue
        observations.setdefault((row[0], row[1]), []).append(
            Observation(
                trade_id=row[0], system=row[1], amendment_seq=int(row[2]),
                value_rate=Decimal(str(row[3])), recorded_at=recorded,
                clock_offset_seconds=offsets[row[1]],
            )
        )

    return Estate(
        trades=trades,
        observations={k: tuple(sorted(v, key=lambda o: o.amendment_seq))
                      for k, v in observations.items()},
        ticks=_ticks(relational, pairs=pairs),
        pips=_corroborated_pips(relational),
        thresholds=_thresholds(relational),
        designated=_designated(relational, trade_ids=[t.trade_id for t in trades]),
        compare_at=compare_at,
        as_of=asked_at,
        tick_spacing_seconds=_tick_spacing(relational),
    )


def _clock_offsets(graph: _Graph, terms: Mapping[str, Any]) -> Mapping[str, int]:
    """Each system's recorded clock offset, from the ledger.

    **Read, never declared.** The offsets are estate facts about three named
    systems; a product that asserted them would be asserting how wrong someone
    else's clock is.
    """
    rows = graph.select(
        f"SELECT ?s ?v FROM <{graph.dataset}> WHERE {{"
        f" ?s <{terms['clock_offset_seconds']}> ?v }}"
    )
    return {r["s"].rsplit("/", 1)[-1].removeprefix("sys-"): int(r["v"]) for r in rows}


def _observation_instants(
    graph: _Graph, terms: Mapping[str, Any], *, trade_ids: Sequence[str]
) -> Mapping[tuple[str, str, int], datetime]:
    """`(trade, system, amendment)` → the instant that system RECORDED.

    The only source of an observation instant in this product.
    `system_trade_record` carries none, and no instant is ever derived from a
    label or from an ingestion time (`FXR-G05`).
    """
    wanted = set(trade_ids)
    rows = graph.select(
        f"SELECT ?s ?sys ?t ?seq FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['system_observation_class']}> ."
        f" ?s <{terms['recorded_by_system']}> ?sys ."
        f" ?s <{terms['system_observed_at']}> ?t ."
        f" ?s <{terms['amendment_seq']}> ?seq }}"
    )
    out: dict[tuple[str, str, int], datetime] = {}
    for row in rows:
        local = row["s"].rsplit("/", 1)[-1].removeprefix("obs-")
        trade_id = local.rsplit("-", 2)[0]
        if trade_id not in wanted:
            continue
        system = row["sys"].rsplit("/", 1)[-1].removeprefix("sys-")
        out[(trade_id, system, int(row["seq"]))] = datetime.fromisoformat(row["t"])
    return out


def _ticks(relational: _Relational, *, pairs: Sequence[str]) -> Mapping[str, tuple[Tick, ...]]:
    series: dict[str, list[Tick]] = {}
    for row in relational.rows(
        "SELECT pair, obs_ts, rate FROM fx_intraday_tick WHERE pair = ANY(%s)"
        " ORDER BY pair, obs_ts",
        (list(pairs),),
    ):
        series.setdefault(row[0], []).append(Tick(obs_ts=row[1], rate=Decimal(str(row[2]))))
    return {k: tuple(v) for k, v in series.items()}


def _tick_spacing(relational: _Relational) -> int:
    """The MEDIAN inter-tick gap in seconds, measured rather than assumed.

    The floor below which a timing decomposition is not evaluable. Measured on
    this estate it is 300 s; reading it from the data means the floor follows
    the series if the series ever changes.
    """
    rows = relational.rows(
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY gap) FROM ("
        " SELECT EXTRACT(EPOCH FROM obs_ts - lag(obs_ts) OVER"
        " (PARTITION BY pair ORDER BY obs_ts)) gap FROM fx_intraday_tick) x"
        " WHERE gap IS NOT NULL"
    )
    return int(rows[0][0]) if rows and rows[0][0] else 300


def _corroborated_pips(relational: _Relational) -> Mapping[str, Decimal]:
    """The DECLARED pip scale, checked against the estate's own table.

    The declaration is the authority and the estate is the corroboration. They
    agree today; a disagreement is refused rather than resolved silently in
    either direction, because either one being wrong is a finding.
    """
    declared = pip_scale()
    estate = {
        row[0]: Decimal(str(row[1]))
        for row in relational.rows("SELECT pair, pip_size FROM fx_pip_size")
    }
    conflicts = {
        pair: (declared[pair], estate[pair])
        for pair in declared.keys() & estate.keys()
        if declared[pair] != estate[pair]
    }
    if conflicts:
        raise PipScaleDisagrees(
            f"the declared pip scale disagrees with `fx_pip_size` for {conflicts!r};"
            " refused rather than resolved, because either one being wrong is a"
            " finding and picking silently would hide it"
        )
    return declared


def _thresholds(relational: _Relational) -> Mapping[str, Decimal]:
    return {
        row[0]: Decimal(str(row[1]))
        for row in relational.rows(
            "SELECT intent, threshold_pips FROM materiality_threshold"
        )
    }


def _designated(
    relational: _Relational, *, trade_ids: Sequence[str]
) -> Mapping[str, str]:
    """The estate's designated break sample, by trade.

    **A sample, never the population** (`CP12-F-07`). Carried so the payload can
    say what the estate designated beside what the product computed, and so the
    two can be compared rather than confused.
    """
    return {
        row[0]: row[1]
        for row in relational.rows(
            "SELECT trade_id, designed_class FROM break_record"
            " WHERE trade_id = ANY(%s)",
            (list(trade_ids),),
        )
    }
