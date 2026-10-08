"""The two source reads, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing.

This module opens PostgreSQL and Fluree, reads, and hands back typed rows. It
holds no fabric call, no gate, no serve and no clock: every instant it uses
arrives as an argument, because a module that read a clock would make the
product's own decision instant unreproducible (`D-IMPL-98`).

**Reads only.** Both stores are read with `SELECT` / SPARQL `SELECT`. The
ledger is append-only so a write is permanent, and nothing here writes to
either (`CP-SPEC-009` §0.3, CLAUDE.md §9 — the curated estate is evidence).

## The coverage window, and why it is a source property rather than an age

A signal source declares the window in which it CLAIMS to hold observations.
Outside that window the source is **absent**, not stale — and the distinction
is load-bearing rather than tidy:

    `intraday_tick` covers 2026-05-11 .. 2026-06-23. Ask it for a rate at
    2026-08-21 and `obs_ts <= asked_at ORDER BY obs_ts DESC LIMIT 1` happily
    returns the 06-23 close, which is then 59 days old. That number is an
    artifact of the query, not a fact about the feed: the feed never claimed
    to cover August. Serving it as a 59-day-old observation would preempt the
    refusal the August scenario exists to demonstrate, and would do it with a
    figure nobody could defend.

So :func:`rate_observations` admits a source only when the decision instant
falls INSIDE the declared window, and a source outside it returns nothing at
all (`CP-SPEC-009` §D.4 scenario 3, `TLP-G22`).
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.sql import SQL, Identifier

HERE = Path(__file__).parent

#: The ledger predicates and classes this product reads, by name. The IRIs are
#: in `artifacts/source-vocabulary.yaml` beside the read that uses them.
VOCABULARY_FILE = HERE / "artifacts" / "source-vocabulary.yaml"


def vocabulary() -> Mapping[str, Any]:
    """The source's own IRIs, read from the artifact rather than spelled here."""
    document: Mapping[str, Any] = yaml.safe_load(
        VOCABULARY_FILE.read_text(encoding="utf-8")
    )
    return document["declaration"]


def _setting(name: str) -> str:
    """One environment variable, refused loudly when absent.

    `backends.yaml` names the VARIABLE; the value is the operator's and never
    enters the tree (`CP-SPEC-009` §C.1).
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. This example reads a live estate; see the"
            " README's Run-it section for the read-only role it needs"
        )
    return value


@dataclass(frozen=True)
class Client:
    """The anchor row. `cash_fact_asof` is a PERIOD END, never an instant."""

    lei: str
    label: str
    mandate_id: str
    intent: str
    home_currency: str
    reported_cash: Decimal
    cash_fact_asof: date


@dataclass(frozen=True)
class Deposit:
    account_id: str
    currency: str
    balance: Decimal
    jurisdiction: str
    setoff_contractual: bool
    setoff_enforceable: bool


@dataclass(frozen=True)
class Position:
    position_id: str
    counterparty_lei: str
    counterparty_label: str
    instrument_kind: str
    currency: str
    notional: Decimal
    maturity_date: date


@dataclass(frozen=True)
class Limit:
    counterparty_lei: str
    limit_pct: Decimal


@dataclass(frozen=True)
class Permitted:
    instrument_kind: str
    max_tenor_days: int


@dataclass(frozen=True)
class Observation:
    """One signal, with the instant it was observed and the class it belongs to.

    `signal_class` keys the §B.6 staleness profile; `source` names which feed
    answered, which is what lets a reader tell an absent source from an old one.
    """

    signal_id: str
    signal_class: str
    source: str
    observed_at: datetime
    value: Decimal
    label: str


@dataclass(frozen=True)
class Posture:
    jurisdiction: str
    intent: str
    level: str
    valid_from: date
    version_id: str


@dataclass(frozen=True)
class Estate:
    """Everything one question needed, as read. No derived figure lives here."""

    client: Client
    deposits: tuple[Deposit, ...]
    positions: tuple[Position, ...]
    limits: tuple[Limit, ...]
    permitted: tuple[Permitted, ...]
    rates: tuple[Observation, ...]
    fx: tuple[Observation, ...]
    postures: tuple[Posture, ...]
    rate_sources_out_of_window: tuple[str, ...]


class UnknownClient(LookupError):
    """The anchor resolves to no `treasury_client` row.

    Raised rather than returning an empty estate: an unknown client is a claim
    about the REQUEST, and a client holding nothing is a claim about the world.
    They mean opposite things and the product answers them differently
    (`TLP-G17`).
    """


class _Relational:
    """PostgreSQL, read-only."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn) as connection:
            cursor = connection.cursor()
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            return list(cursor.fetchall())


class _Graph:
    """The ledger, over SPARQL. Read-only, and no transaction pin is needed.

    The posture overlay is versioned by `validFrom` IN THE DATA, so the answer
    is a function of the decision instant rather than of the store's `t`
    (`CP-SPEC-009` §D.3, `TLP-G10`). A transaction pin would say which store
    state answered, which this product does not claim.
    """

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def select(self, body: str) -> list[Mapping[str, Any]]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read())
        return list(payload["results"]["bindings"])

    @property
    def dataset(self) -> str:
        return self._ledger


def _cell(row: Mapping[str, Any], name: str) -> str:
    value = row.get(name)
    return "" if value is None else str(value.get("value"))


def acquire(*, anchor_lei: str, asked_at: datetime, currencies: Sequence[str] | None) -> Estate:
    """Read everything one question needs, at one decision instant.

    `currencies` narrows the deposit scope, and therefore which FX observations
    are required at all — scope decides participation before freshness decides
    admission (`CP-SPEC-009` §B.6, `TLP-G20`).
    """
    relational = _Relational(
        dsn=_setting("CCF_CP_09_POSTGRES_DSN"),
        schema=_setting("CCF_CP_09_POSTGRES_SCHEMA"),
    )
    graph = _Graph(
        url=_setting("CCF_CP_09_FLUREE_URL"),
        ledger=_setting("CCF_CP_09_FLUREE_LEDGER"),
    )
    terms = vocabulary()

    client_rows = relational.rows(
        "SELECT t.lei, le.legal_name, t.mandate_id, t.intent, t.home_currency,"
        " t.reported_cash, t.cash_fact_asof"
        " FROM treasury_client t JOIN legal_entity le ON le.lei = t.lei"
        " WHERE t.lei = %s",
        (anchor_lei,),
    )
    if not client_rows:
        raise UnknownClient(
            f"treasury client {anchor_lei!r} is not available (404); this"
            " product serves registered treasury clients and fails closed"
            " rather than returning an empty position"
        )
    row = client_rows[0]
    client = Client(
        lei=str(row[0]).strip(), label=str(row[1]), mandate_id=str(row[2]),
        intent=str(row[3]), home_currency=str(row[4]).strip(),
        reported_cash=row[5], cash_fact_asof=row[6],
    )

    wanted = tuple(c.upper() for c in currencies) if currencies else ()
    deposit_sql = (
        "SELECT account_id, currency, balance, jurisdiction,"
        " setoff_contractual, setoff_enforceable FROM deposit_account"
        " WHERE holder_lei = %s"
    )
    deposit_args: list[Any] = [anchor_lei]
    if wanted:
        deposit_sql += " AND upper(currency) = ANY(%s)"
        deposit_args.append(list(wanted))
    deposits = tuple(
        Deposit(str(r[0]), str(r[1]).strip(), r[2], str(r[3]), bool(r[4]), bool(r[5]))
        for r in relational.rows(deposit_sql + " ORDER BY account_id", deposit_args)
    )

    # `currencies` SCOPES BOTH KINDS OF HOLDING, and it has to. §B.4 declares
    # it as `R` scope, and a deposit-only filter would leave positions in three
    # other currencies still requiring a conversion — so a single-currency
    # question would still drag the FX class into participation and §D.4's
    # scenario-3 claim would be false. Measured while building: scoping
    # deposits alone returned three FX pairs on a USD-only request.
    position_sql = (
        "SELECT i.position_id, i.counterparty_lei, le.legal_name,"
        " i.instrument_kind, i.currency, i.notional, i.maturity_date"
        " FROM investment_position i"
        " LEFT JOIN legal_entity le ON le.lei = i.counterparty_lei"
        " WHERE i.holder_lei = %s"
    )
    position_args: list[Any] = [anchor_lei]
    if wanted:
        position_sql += " AND upper(i.currency) = ANY(%s)"
        position_args.append(list(wanted))
    positions = tuple(
        Position(
            position_id=str(r[0]), counterparty_lei=str(r[1]).strip(),
            counterparty_label=str(r[2]) if r[2] else str(r[1]).strip(),
            instrument_kind=str(r[3]), currency=str(r[4]).strip(),
            notional=r[5], maturity_date=r[6],
        )
        for r in relational.rows(
            position_sql + " ORDER BY i.position_id", position_args
        )
    )

    limits = tuple(
        Limit(str(r[0]).strip(), r[1])
        for r in relational.rows(
            "SELECT counterparty_lei, limit_pct FROM concentration_limit"
            " WHERE holder_lei = %s AND intent = %s ORDER BY counterparty_lei",
            (anchor_lei, client.intent),
        )
    )
    permitted = tuple(
        Permitted(str(r[0]), int(r[1]))
        for r in relational.rows(
            "SELECT instrument_kind, max_tenor_days FROM permitted_instrument"
            " WHERE mandate_id = %s ORDER BY instrument_kind",
            (client.mandate_id,),
        )
    )

    rates, out_of_window = rate_observations(relational, asked_at=asked_at)
    fx = fx_observations(
        relational, asked_at=asked_at,
        pairs=_pairs_needed(deposits, positions, home=client.home_currency),
    )
    postures = posture_overlay(
        graph, terms, asked_at=asked_at, intent=client.intent,
        jurisdictions=sorted({d.jurisdiction for d in deposits}),
    )
    return Estate(
        client=client, deposits=deposits, positions=positions, limits=limits,
        permitted=permitted, rates=rates, fx=fx, postures=postures,
        rate_sources_out_of_window=out_of_window,
    )


def _signal_sources() -> Sequence[Mapping[str, Any]]:
    """The declared rate feeds and their coverage windows, from the artifact."""
    document = yaml.safe_load(
        (HERE / "artifacts" / "signal-sources.yaml").read_text(encoding="utf-8")
    )
    sources: Sequence[Mapping[str, Any]] = document["declaration"]["rate_sources"]
    return sources


def rate_observations(
    relational: _Relational, *, asked_at: datetime
) -> tuple[tuple[Observation, ...], tuple[str, ...]]:
    """The intraday-rate class, from whichever declared feed COVERS the instant.

    Returns the observations and the names of the declared feeds whose window
    does not contain `asked_at` — the second value is what lets the payload say
    *absent* rather than leaving a reader to infer it from a silence.
    """
    admitted: list[Observation] = []
    outside: list[str] = []
    for source in _signal_sources():
        start = datetime.fromisoformat(source["covers_from"])
        end = datetime.fromisoformat(source["covers_to"])
        if not start <= asked_at <= end:
            outside.append(str(source["name"]))
            continue
        for row in relational.rows(source["query"], (asked_at,)):
            admitted.append(
                Observation(
                    signal_id=str(row[0]), signal_class=str(source["signal_class"]),
                    source=str(source["name"]), observed_at=row[1],
                    value=row[2], label=str(row[3]),
                )
            )
    return tuple(admitted), tuple(outside)


def _pairs_needed(
    deposits: Sequence[Deposit], positions: Sequence[Position], *, home: str
) -> tuple[str, ...]:
    """Which FX pairs a conversion to `home` actually requires.

    A holding already in the home currency needs no rate, so a single-currency
    scope needs NO FX observation at all and no FX bound can fire (`TLP-G20`).
    """
    held = {d.currency for d in deposits} | {p.currency for p in positions}
    return tuple(sorted(f"{c}/{home}" for c in held if c != home))


def fx_observations(
    relational: _Relational, *, asked_at: datetime, pairs: Sequence[str]
) -> tuple[Observation, ...]:
    """The FX class, one observation per REQUIRED pair. Empty when none is."""
    found: list[Observation] = []
    for pair in pairs:
        base, _, quote = pair.partition("/")
        for stored, inverted in ((f"{base}/{quote}", False), (f"{quote}/{base}", True)):
            rows = relational.rows(
                "SELECT pair, obs_date, rate FROM fx_reference_rate"
                " WHERE pair = %s AND obs_date <= %s"
                " ORDER BY obs_date DESC LIMIT 1",
                (stored, asked_at.date()),
            )
            if not rows:
                continue
            observed = datetime.combine(
                rows[0][1], datetime.min.time(), tzinfo=asked_at.tzinfo
            )
            found.append(
                Observation(
                    signal_id=f"fx:{pair}", signal_class="fx-reference",
                    source="fx_reference_rate", observed_at=observed,
                    value=rows[0][2], label=f"{stored}{' inverted' if inverted else ''}",
                )
            )
            break
    return tuple(found)


def posture_overlay(
    graph: _Graph, terms: Mapping[str, Any], *, asked_at: datetime,
    intent: str, jurisdictions: Sequence[str],
) -> tuple[Posture, ...]:
    """The regulatory posture IN FORCE at the decision instant, per jurisdiction.

    **Effectivity, not age.** The latest `validFrom` at or before `asked_at`
    wins; a version effective later is not stale, it is not yet in force, and a
    version effective earlier is not old, it is superseded. Reading the ledger
    head instead would serve today's posture for a question about June
    (`TLP-G09`, `TLP-G10`).
    """
    if not jurisdictions:
        return ()
    rows = graph.select(
        f"SELECT ?j ?lvl ?vf ?s FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['posture_class']}> ;"
        f" <{terms['posture_jurisdiction']}> ?j ;"
        f" <{terms['posture_intent']}> ?i ;"
        f" <{terms['posture_level']}> ?lvl ;"
        f" <{terms['posture_valid_from']}> ?vf ."
        f' FILTER(?i = "{intent}") }}'
    )
    in_force: dict[str, Posture] = {}
    cut = asked_at.date().isoformat()
    for row in rows:
        jurisdiction = _cell(row, "j")
        valid_from = _cell(row, "vf")
        if jurisdiction not in set(jurisdictions) or valid_from > cut:
            continue
        candidate = Posture(
            jurisdiction=jurisdiction, intent=intent, level=_cell(row, "lvl"),
            valid_from=date.fromisoformat(valid_from),
            version_id=_cell(row, "s").rsplit("/", 1)[-1],
        )
        standing = in_force.get(jurisdiction)
        if standing is None or candidate.valid_from > standing.valid_from:
            in_force[jurisdiction] = candidate
    return tuple(in_force[k] for k in sorted(in_force))
