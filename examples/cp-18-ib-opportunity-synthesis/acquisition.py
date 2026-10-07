"""The estate half of `cib.opportunity-synthesis` — four stores, one order.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's: it takes
settings by name, returns dated claims, and never touches a Control Plane, a
product or a door.

THE ORDER IS THE POINT (`CP-SPEC-018` §D.3). The banker and the coverage
portfolio come first — the candidate universe is the consumer's, which is what
makes this the one consumer-anchored product on the ladder. Then the
departmental read: the restricted and MNPI state, which under Dave's ruling of
2026-09-21 is a CLASSIFICATION input and **not a candidate deletion** — a
restricted prospect stays a candidate and what the restriction bounds is the
evidence admitted for it and what the principal may see. Then the perspective's
plan and the weight vector in force at `as_of`, then the signals, then the
banker's own notes, then the passages.

WHAT THE ENVELOPE'S INPUTS ARE, AND WHERE THEY STOP. The restricted-list rows
and another banker's notes are consumed at this seam and are NOT emitted as
claims. The weight vector IS emitted, on the banker claim, because the
perspective is entitled to know what ranked its book and because replay
reproduces the historical ranking from the snapshot that carries it.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"


class ControlRoomUnreachable(RuntimeError):
    """The departmental store did not answer. A raise, never a governed no."""


class NoPlanForPerspective(RuntimeError):
    """The estate holds no projection plan for this perspective."""


class NoCoveragePortfolio(RuntimeError):
    """This banker covers nothing, so there is no candidate universe to rank."""


class SignalTypeOutsidePlan(ValueError):
    """The caller asked for a signal type its perspective's plan does not carry."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    """Every source name this deployment reads, from its declared artifact."""
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


# =========================================================================
# THE ENVELOPE — what the asking banker may receive, computed first
# =========================================================================


@dataclass(frozen=True)
class Plan:
    """One perspective's projection plan, as the estate declares it."""

    perspective_id: str
    plan_id: str
    plan_version: str
    permitted_signal_types: tuple[str, ...]

    def as_json(self, *, required_classes: Sequence[str]) -> str:
        return json.dumps(
            {
                "perspective_id": self.perspective_id,
                "plan_id": self.plan_id,
                "plan_version": self.plan_version,
                "permitted_signal_types": list(self.permitted_signal_types),
                "required_classes": list(required_classes),
            },
            sort_keys=True,
        )


@dataclass(frozen=True)
class Weights:
    """The weight vector in force, and the version that names it.

    The version is resolved here and never stated by the caller: a banker
    choosing which vector ranks its own book could choose the one that ranks it
    most favourably, which is strictly more than the credential permits
    (`CP-SPEC-018` §B.4).
    """

    weight_version: str
    by_signal_type: Mapping[str, Decimal]

    def as_json(self) -> str:
        return json.dumps(
            {"weight_version": self.weight_version,
             "weights": {k: str(v) for k, v in sorted(self.by_signal_type.items())}},
            sort_keys=True,
        )


@dataclass(frozen=True)
class Record:
    """One admissible claim: its class, its edge, its dated attributes."""

    entity_class: str
    edge_type: str
    entity_uri: str
    attributes: Mapping[str, str]
    dated: date | None


@dataclass(frozen=True)
class Estate:
    """Everything one question admitted, and the envelope that admitted it."""

    banker_id: str
    perspective: str
    plan: Plan | None
    weights: Weights | None
    banker: Mapping[str, str] | None
    portfolio: tuple[str, ...]
    records: tuple[Record, ...]
    half_lives: Mapping[str, int]
    ledger_t: str
    optional_context: Mapping[str, Any] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return self.banker is None


# =========================================================================
# THE READERS — one per substrate, each taking its settings by name
# =========================================================================


class _ControlRoom:
    """The departmental SQLite, opened READ-ONLY."""

    def __init__(self, *, path: str) -> None:
        self._path = path

    def _rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        try:
            connection = sqlite3.connect(f"file:{self._path}?mode=ro", uri=True)
        except sqlite3.Error as unreachable:  # pragma: no cover - environment
            raise ControlRoomUnreachable(f"departmental store unreadable: {unreachable}") from unreachable
        try:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(sql, args)]
        except sqlite3.Error as unreachable:
            raise ControlRoomUnreachable(f"departmental store refused a read: {unreachable}") from unreachable
        finally:
            connection.close()

    def restricted(self, *, table: str, columns: Mapping[str, str]) -> list[Mapping[str, Any]]:
        return self._rows(
            f"select {columns['lei']}, {columns['restriction_type']},"
            f" {columns['added_date']}, {columns['removed_date']} from {table}"
        )

    def notes(self, *, table: str, columns: Mapping[str, str], banker_id: str) -> list[Mapping[str, Any]]:
        names = ", ".join(columns[key] for key in
                          ("note_id", "lei", "banker_id", "note", "signal_type",
                           "materiality", "rank_changing", "created_at"))
        return self._rows(f"select {names} from {table} where {columns['banker_id']} = ?", (banker_id,))


class _Relational:
    """PostgreSQL, read-only, by DSN and schema name."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with psycopg.connect(self._dsn, autocommit=True) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
                cursor.execute(sql, args)
                return [dict(row) for row in cursor.fetchall()]


class _Graph:
    """Fluree — read for the ledger watermark alone."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def watermark(self) -> str:
        """The ledger's transaction `t`, else `unreported`."""
        query = f"SELECT ?s FROM <{self._ledger}> WHERE {{ ?s ?p ?o }} LIMIT 1"
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query", data=query.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                return str(response.headers.get("x-fdb-t") or "unreported")
        except (urllib.error.URLError, TimeoutError):  # pragma: no cover - environment
            return "unreported"


class _Documents:
    """MongoDB — the filing-passage corpus."""

    def __init__(self, *, uri: str, database: str) -> None:
        self._uri, self._database = uri, database

    def passages(
        self, *, collection: str, document_collection: str, leis: Sequence[str], limit: int
    ) -> list[Mapping[str, Any]]:
        """The corpus for these prospects, in TWO steps.

        `passage` carries no `lei`; the corpus reaches a prospect through
        `document.lei`. Resolving documents first is what makes the passage
        read bounded by the portfolio rather than by the whole corpus.
        """
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(self._uri, serverSelectionTimeoutMS=15000)
        try:
            database = client[self._database]
            by_document = {
                str(row["document_id"]): str(row.get("lei") or "")
                for row in database[document_collection].find(
                    {"lei": {"$in": list(leis)}}, {"document_id": 1, "lei": 1}
                )
                if row.get("document_id")
            }
            if not by_document:
                return []
            found = database[collection].find(
                {"document_id": {"$in": list(by_document)}}, limit=limit
            )
            return [{**dict(row), "lei": by_document.get(str(row.get("document_id")), "")}
                    for row in found]
        finally:
            client.close()


# =========================================================================
# ACQUIRE — the envelope from the credential, then everything it admits
# =========================================================================


def acquire(
    *,
    banker_id: str,
    asked_at: datetime,
    as_of: datetime,
    since: datetime,
    perspective: str,
    requested_signal_types: Sequence[str],
    control_room_settings: Mapping[str, str],
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
    document_settings: Mapping[str, str],
) -> Estate:
    """Everything one question admits, in the one order that is safe."""
    terms = vocabulary()
    tables = terms["relational"]["tables"]
    control_room = _ControlRoom(path=control_room_settings["path"])
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])
    documents = _Documents(uri=document_settings["uri"], database=document_settings["db"])

    # 1. The banker. No row -> an EMPTY estate, never a raise (the A6 comparator).
    bankers = relational.rows(
        f"select banker_id, full_name, role, desk from {tables['banker']} where banker_id = %s",
        (banker_id,),
    )
    if not bankers:
        return Estate(banker_id=banker_id, perspective=perspective, plan=None, weights=None,
                      banker=None, portfolio=(), records=(), half_lives={},
                      ledger_t=graph.watermark())
    banker = {key: "" if value is None else str(value) for key, value in bankers[0].items()}

    # 2. The coverage portfolio — the candidate universe, and it is the
    #    CONSUMER's rather than any subject's.
    portfolio = tuple(sorted(
        str(row["lei"]) for row in relational.rows(
            f"select lei from {tables['coverage']} where banker_id = %s", (banker_id,)
        )
    ))

    # 2a. A banker who covers nothing has no candidate universe. That is a
    #     governed refusal by name, not an empty list: an empty ranking would
    #     read as "nothing worth working on this week", which is a different
    #     and false answer (`IBO-G15`).
    if not portfolio:
        raise NoCoveragePortfolio(
            f"banker `{banker_id}` has no row in `{tables['coverage']}`;"
            f" there is no candidate universe to rank"
        )

    # 3. THE DEPARTMENTAL READ. Classification, NOT deletion (Dave, 2026-09-21).
    room = terms["control_room"]
    restricted = _restricted_now(
        control_room.restricted(table=room["restricted_table"], columns=room["restricted_columns"]),
        columns=room["restricted_columns"], at=as_of.date(),
    )

    # 4. The perspective's plan — its ceiling on which signal types exist at all.
    plan = plan_for(relational, perspective_id=_perspective_id(perspective, terms, relational),
                    table=tables["projection_plan"])
    if plan is None:
        raise NoPlanForPerspective(
            f"perspective `{perspective}` has no row in `{tables['projection_plan']}`"
        )
    admitted_types = _admitted_signal_types(plan, requested_signal_types)

    # 5. The weight vector in force at `as_of` — resolved, never requested.
    weights = weights_in_force(relational, perspective_id=plan.perspective_id,
                               table=tables["weight"], at=as_of)
    half_lives = {
        str(row["signal_type"]): int(row["half_life_days"])
        for row in relational.rows(f"select signal_type, half_life_days from {tables['signal_class']}")
    }

    records = _records(
        relational, control_room, documents, terms,
        banker_id=banker_id, portfolio=portfolio, restricted=restricted,
        admitted_types=admitted_types, as_of=as_of, since=since,
    )
    return Estate(
        banker_id=banker_id, perspective=perspective, plan=plan, weights=weights,
        banker=banker, portfolio=portfolio, records=records, half_lives=half_lives,
        ledger_t=graph.watermark(),
        # The optional CP-17 contribution, absent by ruling (`CP-SPEC-018`
        # §F.4.3). Named here rather than omitted, so the served product can
        # say WHICH context it was ranked without (`IBO-G17`, `IBO-G18`).
        optional_context={
            "mnpi_wall_child": "absent",
            "child_count": 0,
            "reason": "complexity-stop",
            "detail": (
                "the paved child seam asks one class exactly one question and"
                " refuses a duplicate `product_class` in `requires`, so the"
                " ruled subset composition is unreachable without reopening"
                " D-IMPL-336 (CP-SPEC-018 F.4.3)"
            ),
        },
    )


def _perspective_id(perspective: str, terms: Mapping[str, Any], relational: _Relational) -> str:
    """This deployment's role name -> the ESTATE's perspective id."""
    rows = relational.rows(
        f"select perspective_id, label from {terms['relational']['tables']['perspective']}"
    )
    for row in rows:
        suffix = str(row["perspective_id"]).rsplit("-", 1)[-1].lower()
        if suffix == perspective.lower():
            return str(row["perspective_id"])
    return perspective


def plan_for(relational: _Relational, *, perspective_id: str, table: str) -> Plan | None:
    """The perspective's own projection plan, or `None`."""
    rows = relational.rows(
        f"select projection_plan_id, perspective_id, plan_version, permitted_signal_types"
        f" from {table} where perspective_id = %s", (perspective_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return Plan(
        perspective_id=str(row["perspective_id"]),
        plan_id=str(row["projection_plan_id"]),
        plan_version=str(row["plan_version"]),
        permitted_signal_types=tuple(sorted(str(t) for t in (row["permitted_signal_types"] or []))),
    )


def planned_perspectives(*, relational_settings: Mapping[str, str]) -> tuple[str, ...]:
    """Every perspective the estate holds a plan for, as this deployment names them."""
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    table = vocabulary()["relational"]["tables"]["projection_plan"]
    return tuple(sorted(
        str(row["perspective_id"]).rsplit("-", 1)[-1].lower()
        for row in relational.rows(f"select perspective_id from {table}")
    ))


def weights_in_force(
    relational: _Relational, *, perspective_id: str, table: str, at: datetime
) -> Weights:
    """The weight vector this perspective ranks under at `at`.

    THE VERSION IS RESOLVED HERE, never stated by the caller. This estate
    carries two versions and no effective date, so the version in force is the
    highest one at or below the Control Plane's declared ceiling — which this
    deployment declares as the latest version, and which a later estate
    carrying effective dates would resolve temporally instead. Recorded as a
    finding rather than pretended away.
    """
    del at
    rows = relational.rows(
        f"select weight_version, signal_type, weight from {table} where perspective_id = %s",
        (perspective_id,),
    )
    if not rows:
        return Weights(weight_version="none", by_signal_type={})
    version = max(str(row["weight_version"]) for row in rows)
    return Weights(
        weight_version=version,
        by_signal_type={
            str(row["signal_type"]): Decimal(str(row["weight"]))
            for row in rows if str(row["weight_version"]) == version
        },
    )


def _restricted_now(
    rows: Sequence[Mapping[str, Any]], *, columns: Mapping[str, str], at: date
) -> Mapping[str, str]:
    """`lei` -> restriction type, for restrictions in force at `at`."""
    live: dict[str, str] = {}
    for row in rows:
        removed = _as_date(row.get(columns["removed_date"]))
        added = _as_date(row.get(columns["added_date"]))
        if added is not None and added > at:
            continue
        if removed is not None and removed <= at:
            continue
        live[str(row[columns["lei"]])] = str(row[columns["restriction_type"]])
    return live


def _admitted_signal_types(plan: Plan, requested: Sequence[str]) -> tuple[str, ...]:
    """The plan's set, narrowed by the request — and refused if widened.

    A type OUTSIDE the plan is refused by name rather than silently dropped
    (`IBO-G14`): asking for a type the plan does not carry is asking for more
    than the credential permits, and the element-wise containment of a
    set-valued request parameter is the deployment's seam intersection today.
    """
    permitted = set(plan.permitted_signal_types)
    if not requested:
        return plan.permitted_signal_types
    outside = sorted(set(requested) - permitted)
    if outside:
        raise SignalTypeOutsidePlan(
            f"signal types {outside} are not in projection plan `{plan.plan_id}`"
            f" for perspective `{plan.perspective_id}`; a type outside the plan is"
            f" refused rather than dropped"
        )
    return tuple(sorted(set(requested)))


def required_classes(plan: Plan, terms: Mapping[str, Any]) -> tuple[str, ...]:
    """The classes this perspective needs for completeness (`C`)."""
    del plan, terms
    return ("banker", "prospect", "signal", "standing_signal", "note")


# =========================================================================
# THE CLAIMS — only what the envelope admits, edges first at the seam above
# =========================================================================


def _records(
    relational: _Relational, control_room: _ControlRoom, documents: _Documents,
    terms: Mapping[str, Any], *, banker_id: str, portfolio: Sequence[str],
    restricted: Mapping[str, str], admitted_types: Sequence[str],
    as_of: datetime, since: datetime,
) -> tuple[Record, ...]:
    """Every admissible claim, minted only if the envelope admits its class."""
    prefixes = terms["entity_uri_prefix"]
    assignment = terms["classification"]["assignment"]
    tables = terms["relational"]["tables"]
    records: list[Record] = []
    if not portfolio:
        return ()

    # The prospects. A RESTRICTED prospect REMAINS A CANDIDATE (Dave,
    # 2026-09-21): the restriction is carried as an attribute so the
    # ranking and the gate can bound its evidence and its disclosure.
    mandates = {
        str(row["lei"]): row for row in relational.rows(
            f"select lei, mandate_type, stated_appetite from {tables['mandate']}"
            f" where lei = any(%s)", (list(portfolio),),
        )
    }
    mnpi = {
        str(row["lei"]) for row in relational.rows(
            f"select distinct lei from {tables['deal']} where mnpi_bearing and lei = any(%s)",
            (list(portfolio),),
        )
    }
    for row in relational.rows(
        f"select lei, legal_name from {tables['legal_entity']} where lei = any(%s)",
        (list(portfolio),),
    ):
        lei = str(row["lei"])
        mandate = mandates.get(lei, {})
        records.append(Record(
            entity_class="prospect", edge_type="coversProspect",
            entity_uri=f"{prefixes['prospect']}{lei}",
            attributes={
                "lei": lei, "legal_name": str(row["legal_name"] or ""),
                "classification": assignment["prospect"],
                "restriction_type": restricted.get(lei, ""),
                "mnpi_bearing": "true" if lei in mnpi else "false",
                "mandate_type": str(mandate.get("mandate_type") or ""),
                "stated_appetite": str(mandate.get("stated_appetite") or ""),
            },
            dated=None,
        ))

    # The signals, one read per declared source, bounded by the window.
    for signal_type in admitted_types:
        source = terms["signal_sources"].get(signal_type)
        if source is None or source.get("unsourced"):
            continue
        standing = bool(source.get("standing"))
        for lei, dated, detail, signal_id in _signal_rows(
            relational, source, portfolio=portfolio, since=since, as_of=as_of,
        ):
            if standing:
                records.append(Record(
                    entity_class="standing_signal", edge_type="hasStandingSignal",
                    entity_uri=f"{prefixes['standing_signal']}{signal_type}:{signal_id}",
                    attributes={
                        "signal_id": signal_id, "lei": lei, "signal_type": signal_type,
                        "effective_on": dated.isoformat(), "detail": detail,
                        "classification": assignment["standing_signal"],
                    },
                    dated=None,
                ))
                continue
            records.append(Record(
                entity_class="signal", edge_type="hasSignal",
                entity_uri=f"{prefixes['signal']}{signal_type}:{signal_id}",
                attributes={
                    "signal_id": signal_id, "lei": lei, "signal_type": signal_type,
                    "observed_on": dated.isoformat(), "detail": detail,
                    "classification": assignment["signal_public"],
                },
                dated=dated,
            ))

    # THE BANKER'S OWN NOTES, and no other banker's. `banker-local`.
    room = terms["control_room"]
    columns = room["note_columns"]
    for note in control_room.notes(table=room["note_table"], columns=columns, banker_id=banker_id):
        lei = str(note[columns["lei"]] or "")
        if lei not in set(portfolio):
            continue
        records.append(Record(
            entity_class="note", edge_type="hasLocalNote",
            entity_uri=f"{prefixes['note']}{note[columns['note_id']]}",
            attributes={
                "note_id": str(note[columns["note_id"]]), "lei": lei,
                "banker_id": str(note[columns["banker_id"]] or ""),
                "signal_type": str(note[columns["signal_type"]] or "banker_local_note"),
                "materiality": str(note[columns["materiality"]] or ""),
                "rank_changing": str(note[columns["rank_changing"]] or ""),
                "note": str(note[columns["note"]] or "")[:400],
                "classification": assignment["note"],
            },
            dated=_as_date(note.get(columns["created_at"])),
        ))

    # The passages, as evidence. Similarity ranks these behind Policy.
    fields = terms["documents"]["fields"]
    for passage in documents.passages(
        collection=terms["documents"]["collection"],
        document_collection=terms["documents"]["document_collection"],
        leis=list(portfolio), limit=400,
    ):
        identifier = str(passage.get(fields["passage_id"]) or passage.get("_id") or "")
        if not identifier:
            continue
        records.append(Record(
            entity_class="passage", edge_type="hasPassage",
            entity_uri=f"{prefixes['passage']}{identifier}",
            attributes={
                "passage_id": identifier,
                "document_id": str(passage.get(fields["document_id"]) or ""),
                "lei": str(passage.get(fields["lei"]) or ""),
                "text": str(passage.get(fields["text"]) or "")[:600],
                "classification": assignment["passage"],
            },
            dated=None,
        ))
    return tuple(records)


def _signal_rows(
    relational: _Relational, source: Mapping[str, Any], *,
    portfolio: Sequence[str], since: datetime, as_of: datetime,
) -> list[tuple[str, date, str, str]]:
    """One declared source's rows as `(lei, dated, detail, signal_id)`."""
    table = source["table"]
    date_column = source["date_column"]
    lei_column = source["lei_column"]
    detail = source.get("detail_columns", [])
    join_table = source.get("join_table")
    selected = ", ".join([f"j.{lei_column}" if join_table else f"t.{lei_column}",
                          f"t.{date_column}", *[f"t.{column}" for column in detail]])
    clauses = [f"j.{lei_column} = any(%s)" if join_table else f"t.{lei_column} = any(%s)"]
    args: list[Any] = [list(portfolio)]
    if source.get("filter_column"):
        clauses.append(f"t.{source['filter_column']} = %s")
        args.append(source["filter_value"])
    join = f" join {join_table} j on j.{source['join_column']} = t.{source['join_column']}" if join_table else ""
    sql = f"select {selected} from {table} t{join} where {' and '.join(clauses)} limit 600"  # noqa: S608
    out: list[tuple[str, date, str, str]] = []
    for index, row in enumerate(relational.rows(sql, tuple(args))):
        values = list(row.values())
        lei, dated = str(values[0]), _as_date(values[1])
        if dated is None or not _inside_window(dated, source, since=since, as_of=as_of):
            continue
        rendered = "; ".join(f"{name}={values[2 + position]}" for position, name in enumerate(detail))
        out.append((lei, dated, rendered[:240], f"{table}:{index}"))
    nearest = source.get("nearest")
    if nearest:
        # Keep the N NEAREST per prospect, so a prospect with many instruments
        # does not outrank one with a nearer wall purely on volume.
        kept: dict[str, list[tuple[str, date, str, str]]] = {}
        for entry in sorted(out, key=lambda e: e[1]):
            kept.setdefault(entry[0], []).append(entry)
        out = [entry for entries in kept.values() for entry in entries[: int(nearest)]]
    return out


def _inside_window(
    dated: date, source: Mapping[str, Any], *, since: datetime, as_of: datetime
) -> bool:
    """Whether a signal's date falls inside its declared window.

    Almost every signal looks BACKWARD from the decision instant. The maturity
    wall looks FORWARD, because upcoming debt is the signal; a backward window
    admits none of this estate's maturities at all.
    """
    if source.get("window") == "forward":
        horizon = as_of.date() + timedelta(days=int(source.get("forward_days", 1095)))
        return as_of.date() <= dated <= horizon
    return since.date() <= dated <= as_of.date()


def principal_bankers(*, relational_settings: Mapping[str, str]) -> Mapping[str, str]:
    """`banker_id` -> desk, from the estate's own roster."""
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    table = vocabulary()["relational"]["tables"]["banker"]
    return {
        str(row["banker_id"]): str(row["desk"] or "")
        for row in relational.rows(f"select banker_id, desk from {table}")
    }


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for parse in (
        lambda t: date.fromisoformat(t[:10]),
        lambda t: datetime.strptime(t[:8], "%Y%m%d").date(),  # noqa: DTZ007
        # `31-MAR-2026` — the shape `institutional_holder.report_period` uses.
        lambda t: datetime.strptime(t[:11], "%d-%b-%Y").date(),  # noqa: DTZ007
    ):
        try:
            return parse(text)
        except ValueError:
            continue
    return None
