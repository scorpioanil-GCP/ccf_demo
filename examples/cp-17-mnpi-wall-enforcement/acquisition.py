"""The source legs of `cib.mnpi-wall` — reads only, and no `ccf` import.

[ADAPT] this module to your own systems of record. It returns frozen
dataclasses in the sources' vocabulary; `deployment.py` turns them into
`SignalEnvelope`s. Every table, collection, predicate, classification rule
and edge name comes from `artifacts/source-vocabulary.yaml`; nothing here
holds one of its own (CLAUDE.md §6.4).

THE ENVELOPE IS COMPUTED HERE, FROM THE CREDENTIAL (`CP-SPEC-017` §D.3
step 1). Which claims a principal's per-request fabric receives is decided
by the principal's own projection-plan row (axis 1, the vocabulary of edge
types; axis 2, the permitted classifications) with the walled classification
unlocked per issuer by a wall crossing that is VALID at `asked_at` and had
been ASSERTED by `known_as_of` — the two clocks of the control room's own
record. The restricted list is read FIRST and is mandatory: without it no
principal is served. Wall state, the restricted list, embargo windows and
the Reg FD event are envelope INPUTS; none is emitted as a claim.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.sql import SQL, Identifier
from pymongo import MongoClient

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"


class ControlRoomUnreachable(RuntimeError):
    """The departmental store could not be read — a mandatory input (`MWE-G09`)."""


class NoPlanForPrincipal(RuntimeError):
    """The door entitled a principal the estate holds no projection plan for."""


def vocabulary() -> Mapping[str, Any]:
    document = yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))
    declaration: Mapping[str, Any] = document["declaration"]
    return declaration


# =========================================================================
# THE SOURCES' VOCABULARY, AS FROZEN DATA
# =========================================================================


@dataclass(frozen=True)
class Plan:
    """One principal's projection-plan row — the envelope's ceiling."""

    plan_id: str
    plan_version: str
    permitted_edge_types: tuple[str, ...]
    permitted_classifications: tuple[str, ...]
    permitted_document_types: tuple[str, ...]

    def as_json(self, *, required_classes: Sequence[str]) -> str:
        return json.dumps(
            {
                "plan_id": self.plan_id,
                "plan_version": self.plan_version,
                "permitted_edge_types": sorted(self.permitted_edge_types),
                "permitted_classifications": sorted(self.permitted_classifications),
                "required_classes": sorted(required_classes),
            },
            sort_keys=True,
        )


@dataclass(frozen=True)
class Record:
    """One admissible claim about the issuer, in the deployment's vocabulary."""

    entity_class: str
    entity_uri: str
    edge_type: str
    attributes: Mapping[str, str]
    dated: date | None


@dataclass(frozen=True)
class Estate:
    """What one question, under one principal, may know about one issuer."""

    lei: str
    principal_id: str
    issuer: Mapping[str, str] | None
    plan: Plan | None
    over_wall: bool
    restriction: Mapping[str, str] | None
    reg_fd: Mapping[str, str] | None
    records: tuple[Record, ...]
    ledger_t: str

    @property
    def empty(self) -> bool:
        return self.issuer is None


# =========================================================================
# THE READERS — one per store, reads only
# =========================================================================


class _ControlRoom:
    """The departmental SQLite, opened read-only."""

    def __init__(self, *, path: str) -> None:
        self._path = path

    def restriction(self, *, table: str, lei: str, at: date) -> Mapping[str, str] | None:
        try:
            connection = sqlite3.connect(f"file:{self._path}?mode=ro", uri=True)
        except sqlite3.Error as failed:
            raise ControlRoomUnreachable(f"control room at `{self._path}` cannot be opened: {failed}") from failed
        try:
            cursor = connection.execute(
                f"SELECT lei, legal_name, ticker, restriction_type, added_date, removed_date,"
                f" added_by, reason_code FROM {table} WHERE lei = ?",
                (lei,),
            )
            names = [column[0] for column in cursor.description]
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
        except sqlite3.Error as failed:
            raise ControlRoomUnreachable(f"control room at `{self._path}` cannot be read: {failed}") from failed
        finally:
            connection.close()
        in_force = [
            row for row in rows
            if _as_date(row["added_date"]) is not None
            and _as_date(row["added_date"]) <= at
            and (row["removed_date"] is None or _as_date(row["removed_date"]) > at)
        ]
        if not in_force:
            return None
        chosen = sorted(in_force, key=lambda row: str(row["added_date"]))[-1]
        return {key: "" if value is None else str(value) for key, value in chosen.items()}


class _Relational:
    """PostgreSQL, one connection per read. Reads only."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor = connection.execute(sql, params)
            names = [column.name for column in cursor.description]
            return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


class _Graph:
    """Fluree, over SPARQL with an explicit `FROM`. Reads only."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def select(self, query: str) -> list[Mapping[str, str]]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query",
            data=query.replace("FROM <LEDGER>", f"FROM <{self._ledger}>").encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            document = json.loads(response.read())
        return [
            {key: value["value"] for key, value in binding.items()}
            for binding in document["results"]["bindings"]
        ]

    def watermark(self) -> str:
        """The ledger's transaction `t` as the store reports it, else `unreported`."""
        name, _, branch = self._ledger.partition(":")
        branch = branch or "main"
        try:
            with urllib.request.urlopen(f"{self._url}/v1/fluree/ledgers", timeout=60) as response:
                listing = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError):
            return "unreported"
        for entry in listing if isinstance(listing, list) else []:
            if entry.get("name") == name and (entry.get("branch") or "main") == branch:
                return str(entry.get("t", "unreported"))
        return "unreported"


# =========================================================================
# THE ACQUISITION — the envelope computed from the credential
# =========================================================================


def acquire(
    *,
    lei: str,
    asked_at: datetime,
    known_as_of: datetime,
    principal_id: str,
    control_room_settings: Mapping[str, str],
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
    document_settings: Mapping[str, str],
) -> Estate:
    """Read the issuer as `principal_id` may see it at `asked_at` / `known_as_of`.

    The order is the contract (`CP-SPEC-017` §D.3 step 1): the control room
    first, then the issuer, then the principal's plan, then the wall state
    and the Reg FD event, then the records — and only the records inside the
    envelope are returned.
    """
    terms = vocabulary()
    as_of_date = asked_at.astimezone(UTC).date()
    known_date = known_as_of.astimezone(UTC).date()
    tables = terms["relational"]["tables"]

    # 1. The control room, first and mandatory.
    control_room = _ControlRoom(path=control_room_settings["path"])
    restriction = control_room.restriction(table=terms["control_room"]["table"], lei=lei, at=as_of_date)

    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])

    # 2. The issuer. No row → an EMPTY estate, never a raise (the A6 comparator).
    issuer_rows = relational.rows(
        f"SELECT lei, legal_name, legal_jurisdiction, entity_status FROM {tables['issuer']} WHERE lei = %s",
        (lei,),
    )
    if not issuer_rows:
        return Estate(lei=lei, principal_id=principal_id, issuer=None, plan=None, over_wall=False,
                      restriction=restriction, reg_fd=None, records=(), ledger_t=graph.watermark())
    issuer = {key: "" if value is None else str(value) for key, value in issuer_rows[0].items()}

    # 3. The principal's plan — the envelope's ceiling.
    plan = plan_for(relational, principal_id=principal_id, table=tables["projection_plan"])
    if plan is None:
        raise NoPlanForPrincipal(f"principal `{principal_id}` has no row in `{tables['projection_plan']}`")

    # 4. Wall state on two clocks, and the Reg FD event.
    over_wall = _over_wall(graph, terms, principal_id=principal_id, lei=lei,
                           valid_at=as_of_date, known_by=known_date)
    reg_fd = _reg_fd(graph, terms, lei=lei, at=as_of_date)

    # 5–6. The records inside the envelope.
    records = _records(relational, graph, terms, lei=lei, plan=plan, over_wall=over_wall,
                       tables=tables, document_settings=document_settings)

    return Estate(lei=lei, principal_id=principal_id, issuer=issuer, plan=plan, over_wall=over_wall,
                  restriction=restriction, reg_fd=reg_fd, records=records, ledger_t=graph.watermark())


def plan_for(relational: _Relational, *, principal_id: str, table: str) -> Plan | None:
    rows = relational.rows(
        f"SELECT projection_plan_id, plan_version, permitted_edge_types, permitted_classifications,"
        f" permitted_document_types FROM {table} WHERE principal_id = %s",
        (principal_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return Plan(
        plan_id=str(row["projection_plan_id"]),
        plan_version=str(row["plan_version"]),
        permitted_edge_types=tuple(str(item) for item in row["permitted_edge_types"]),
        permitted_classifications=tuple(str(item) for item in row["permitted_classifications"]),
        permitted_document_types=tuple(str(item) for item in row["permitted_document_types"]),
    )


def principal_roles(*, relational_settings: Mapping[str, str]) -> Mapping[str, str]:
    """`principal_id` → `perspective` for every principal the estate declares.

    Read once at open by the door's perspective resolver (`CP-SPEC-017`
    §D.3 step 0). Every principal is mapped — the ungranted one included —
    so the resolver never raises; entitlement, not identity, refuses.
    """
    terms = vocabulary()
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    rows = relational.rows(f"SELECT principal_id, perspective FROM {terms['relational']['tables']['principal']}")
    return {str(row["principal_id"]): str(row["perspective"]) for row in rows}


def planned_principals(*, relational_settings: Mapping[str, str]) -> tuple[str, ...]:
    """The principals the estate holds a projection plan for — the grantable set."""
    terms = vocabulary()
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    rows = relational.rows(
        f"SELECT DISTINCT principal_id FROM {terms['relational']['tables']['projection_plan']} ORDER BY 1"
    )
    return tuple(str(row["principal_id"]) for row in rows)


def required_classes(plan: Plan, terms: Mapping[str, Any]) -> tuple[str, ...]:
    """The entity classes a plan's edge vocabulary reaches — `C_required` (§E.2)."""
    classes = {"issuer"}
    for entity_class, spec in terms["edges"].items():
        names = _edge_names(spec)
        if any(name in plan.permitted_edge_types for name in names):
            classes.add(entity_class)
    classes.discard("family_member")  # optional for every role (§E.2)
    return tuple(sorted(classes))


# --- placing a request value in SPARQL ----------------------------------------

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


# --- the wall, the Reg FD event ------------------------------------------------


def _over_wall(graph: _Graph, terms: Mapping[str, Any], *, principal_id: str, lei: str,
               valid_at: date, known_by: date) -> bool:
    g = terms["graph"]
    p = _predicates(g)
    rows = graph.select(
        f"SELECT ?validFrom ?assertedAt FROM <LEDGER> WHERE {{"
        f" ?s a <{g['prefix']}{g['types']['wall_crossing']}> ;"
        f" {p['principal_id']} ?principal ; {p['lei']} ?lei ;"
        f" {p['valid_from']} ?validFrom ; {p['asserted_at']} ?assertedAt ."
        f" FILTER(STR(?principal) = {_literal(principal_id)} && STR(?lei) = {_literal(lei)}) }}"
    )
    for row in rows:
        valid_from, asserted_at = _as_date(row["validFrom"]), _as_date(row["assertedAt"])
        if valid_from is not None and asserted_at is not None and valid_from <= valid_at and asserted_at <= known_by:
            return True
    return False


def _reg_fd(graph: _Graph, terms: Mapping[str, Any], *, lei: str, at: date) -> Mapping[str, str] | None:
    g = terms["graph"]
    p = _predicates(g)
    rows = graph.select(
        f"SELECT ?event ?validFrom ?widens FROM <LEDGER> WHERE {{"
        f" ?event a <{g['prefix']}{g['types']['reg_fd_event']}> ; {p['lei']} ?lei ;"
        f" {p['valid_from']} ?validFrom ; {p['widens_access']} ?widens ."
        f" FILTER(STR(?lei) = {_literal(lei)}) }}"
    )
    events = []
    for row in rows:
        valid_from = _as_date(row["validFrom"])
        if valid_from is not None and valid_from <= at:
            events.append({"event_id": row["event"].rsplit("/", 1)[-1], "valid_from": valid_from.isoformat(),
                           "widens_access": str(row["widens"]).lower()})
    if not events:
        return None
    return sorted(events, key=lambda event: event["valid_from"])[-1]


# --- the records ----------------------------------------------------------------


def _records(relational: _Relational, graph: _Graph, terms: Mapping[str, Any], *, lei: str, plan: Plan,
             over_wall: bool, tables: Mapping[str, str], document_settings: Mapping[str, str]) -> tuple[Record, ...]:
    classify = terms["classification"]["assignment"]
    walled = terms["classification"]["walled"]
    prefixes = terms["entity_uri_prefix"]
    edges = terms["edges"]

    bounded = set(terms["classification"]["bounded_classes"])

    def admitted(entity_class: str, edge_type: str, classification: str) -> bool:
        if edge_type not in plan.permitted_edge_types:
            return False
        if entity_class in bounded and classification not in plan.permitted_classifications:
            return False
        return classification != walled or over_wall

    records: list[Record] = []

    for row in relational.rows(
        f"SELECT deal_id, deal_type, stage, opened_date, mnpi_bearing FROM {tables['deal']} WHERE lei = %s ORDER BY deal_id",
        (lei,),
    ):
        flagged = bool(row[classify["deal_engagement"]["flag"]])
        classification = classify["deal_engagement"]["flagged" if flagged else "otherwise"]
        edge_type = edges["deal_engagement"]["flagged" if flagged else "otherwise"]
        if admitted("deal_engagement", edge_type, classification):
            records.append(Record(
                entity_class="deal_engagement", entity_uri=f"{prefixes['deal_engagement']}{row['deal_id']}",
                edge_type=edge_type, dated=row["opened_date"],
                attributes=_strings(deal_id=row["deal_id"], deal_type=row["deal_type"], stage=row["stage"],
                                    opened_date=row["opened_date"], mnpi_bearing=str(flagged).lower(),
                                    classification=classification),
            ))

    for row in relational.rows(
        f"SELECT interaction_id, interaction_type, interaction_date, deal_id, mnpi_bearing, need_to_know"
        f" FROM {tables['interaction']} WHERE lei = %s ORDER BY interaction_id",
        (lei,),
    ):
        flagged = any(bool(row[flag]) for flag in classify["interaction"]["flags"])
        classification = classify["interaction"]["flagged" if flagged else "otherwise"]
        edge_type = edges["interaction"]
        if admitted("interaction", edge_type, classification):
            records.append(Record(
                entity_class="interaction", entity_uri=f"{prefixes['interaction']}{row['interaction_id']}",
                edge_type=edge_type, dated=row["interaction_date"],
                attributes=_strings(interaction_id=row["interaction_id"], interaction_type=row["interaction_type"],
                                    interaction_date=row["interaction_date"], deal_id=row["deal_id"],
                                    classification=classification),
            ))

    for row in relational.rows(
        f"SELECT position_id, book, quantity, as_of FROM {tables['position']} WHERE lei = %s ORDER BY position_id",
        (lei,),
    ):
        classification = classify["position"]
        edge_type = edges["position"]
        if admitted("position", edge_type, classification):
            records.append(Record(
                entity_class="position", entity_uri=f"{prefixes['position']}{row['position_id']}",
                edge_type=edge_type, dated=row["as_of"],
                attributes=_strings(position_id=row["position_id"], book=row["book"], quantity=row["quantity"],
                                    as_of=row["as_of"], classification=classification),
            ))

    mongo = MongoClient(document_settings["uri"], serverSelectionTimeoutMS=15000)[document_settings["db"]]
    collection = terms["documents"]["collections"]["research_note"]
    for note in mongo[collection].find({"lei": lei}).sort("note_id", 1):
        published = str(note.get("status")) == "published"
        classification = classify["research_note"]["status_published" if published else "otherwise"]
        edge_type = edges["research_note"]
        if admitted("research_note", edge_type, classification):
            body = str(note.get("body") or "")
            records.append(Record(
                entity_class="research_note", entity_uri=f"{prefixes['research_note']}{note['note_id']}",
                edge_type=edge_type, dated=_as_date(note.get("authored_date")),
                attributes=_strings(note_id=note["note_id"], title=note.get("title"), authored_date=note.get("authored_date"),
                                    status=note.get("status"), classification=classification, body=body,
                                    content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest()),
            ))

    for relation, member in _family(graph, terms, lei=lei):
        classification = classify["family_member"]
        if admitted("family_member", relation, classification):
            records.append(Record(
                entity_class="family_member", entity_uri=f"{prefixes['family_member']}{member['lei']}",
                edge_type=relation, dated=None,
                attributes=_strings(lei=member["lei"], legal_name=member.get("legal_name"), relation=relation,
                                    classification=classification),
            ))

    return tuple(records)


def _family(graph: _Graph, terms: Mapping[str, Any], *, lei: str) -> list[tuple[str, Mapping[str, str]]]:
    """The issuer's `owns` / `controls` neighbors in the ledger, by LEI."""
    g = terms["graph"]
    p = _predicates(g)
    lei_predicate, label = p["lei"], p["label"]
    found: list[tuple[str, Mapping[str, str]]] = []
    for relation in terms["edges"]["family_member"]:
        predicate = p[relation]
        for direction in (
            f"?issuer {lei_predicate} ?issuerLei . ?issuer {predicate} ?member .",
            f"?issuer {lei_predicate} ?issuerLei . ?member {predicate} ?issuer .",
        ):
            rows = graph.select(
                f"SELECT ?memberLei ?memberLabel FROM <LEDGER> WHERE {{ {direction}"
                f" ?member {lei_predicate} ?memberLei . OPTIONAL {{ ?member {label} ?memberLabel }}"
                f" FILTER(STR(?issuerLei) = {_literal(lei)}) }}"
            )
            for row in rows:
                found.append((relation, {"lei": row["memberLei"], "legal_name": row.get("memberLabel", "")}))
    return found


# --- small helpers ----------------------------------------------------------------


def _predicates(graph_terms: Mapping[str, Any]) -> Mapping[str, str]:
    """Every predicate as `<IRI>`: a bare name takes the prefix, a full IRI stands."""
    prefix = graph_terms["prefix"]
    return {
        name: f"<{value}>" if str(value).startswith("http") else f"<{prefix}{value}>"
        for name, value in graph_terms["predicates"].items()
    }


def _edge_names(spec: Any) -> tuple[str, ...]:
    if isinstance(spec, str):
        return (spec,)
    if isinstance(spec, list):
        return tuple(str(item) for item in spec)
    return (str(spec["flagged"]), str(spec["otherwise"]))


def _strings(**values: Any) -> Mapping[str, str]:
    return {key: "" if value is None else str(value) for key, value in values.items()}


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
