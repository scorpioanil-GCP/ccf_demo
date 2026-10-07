"""The estate half of `compliance.aml-typology` — four stores, one order.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's: it takes
settings by name, returns dated claims, and never touches a Control Plane, a
product or a door.

THE ORDER IS THE POINT (`CP-SPEC-019` §D.3). The departmental store is read
FIRST, before any enterprise source is opened: the existence of a SAR is
itself restricted, so the classification that bounds the fabric is read before
there is a fabric to bound. Then the posture effective at `as_of` and its
disposition rules, which compute the permitted set; then the alert and its
network; then the advisory passages. A claim the envelope excludes is never
minted, so nothing downstream can serve it by mistake.

WHAT THE ENVELOPE'S INPUTS ARE, AND WHERE THEY STOP. The SAR classification
rows, the disposition rule set and the residency constraint are consumed at
this seam and are NOT emitted as claims. The *permitted disposition set* IS
emitted, on the alert claim, because the asking perspective is entitled to
know what it may propose and both `assess` and the declared gate read it off
the view.
"""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
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


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    """Every source name this deployment reads, from its declared artifact."""
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


# =========================================================================
# THE ENVELOPE — what the asking perspective may receive, computed first
# =========================================================================


@dataclass(frozen=True)
class Plan:
    """One perspective's projection plan, as the estate declares it."""

    perspective: str
    elements: tuple[str, ...]

    def as_json(self, *, required_classes: Sequence[str]) -> str:
        return json.dumps(
            {
                "perspective": self.perspective,
                "elements": list(self.elements),
                "required_classes": list(required_classes),
            },
            sort_keys=True,
        )


@dataclass(frozen=True)
class Posture:
    """The filing posture in force at the asked instant."""

    posture_id: str
    effective_from: str

    def as_json(self) -> str:
        return json.dumps(
            {"posture_id": self.posture_id, "effective_from": self.effective_from},
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

    alert_id: str
    perspective: str
    plan: Plan | None
    posture: Posture | None
    permitted: tuple[str, ...]
    alert: Mapping[str, str] | None
    records: tuple[Record, ...]
    ledger_t: str
    typologies: tuple[str, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return self.alert is None


# =========================================================================
# THE READERS — one per substrate, each taking its settings by name
# =========================================================================


class _ControlRoom:
    """The departmental SQLite, read-only. Opened FIRST."""

    def __init__(self, *, path: str) -> None:
        self._path = path

    def sar_rows(self, *, table: str, columns: Mapping[str, str], alert_id: str) -> list[Mapping[str, str]]:
        try:
            with sqlite3.connect(f"file:{self._path}?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                cur = db.execute(
                    f"select {columns['sar_id']}, {columns['alert_id']},"
                    f" {columns['classification']}, {columns['visible_to']}"
                    f" from {table} where {columns['alert_id']} = ?",
                    (alert_id,),
                )
                return [{k: "" if v is None else str(v) for k, v in dict(row).items()} for row in cur.fetchall()]
        except sqlite3.Error as unreachable:  # pragma: no cover - substrate fault
            raise ControlRoomUnreachable(str(unreachable)) from unreachable


class _Relational:
    """The estate's Postgres, read-only, under the named search path."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn = dsn
        self._schema = schema

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        import psycopg  # noqa: PLC0415 - the driver is the deployment's
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, params)
            names = [column.name for column in cursor.description or ()]
            return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


class _Graph:
    """The estate's Fluree, read-only, through its SPARQL endpoint."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url = url.rstrip("/")
        self._ledger = ledger

    def select(self, query: str) -> list[Mapping[str, str]]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query",
            data=query.replace("FROM <LEDGER>", f"FROM <{self._ledger}>").encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310
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
            with urllib.request.urlopen(f"{self._url}/v1/fluree/ledgers", timeout=60) as response:  # noqa: S310
                listing = json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError):
            return "unreported"
        for entry in listing if isinstance(listing, list) else []:
            if entry.get("name") == name and (entry.get("branch") or "main") == branch:
                return str(entry.get("t", "unreported"))
        return "unreported"


class _Documents:
    """The estate's MongoDB, read-only, for the advisory corpus."""

    def __init__(self, *, uri: str, database: str) -> None:
        self._uri = uri
        self._database = database

    def passages(self, *, collection: str, document_regex: str) -> list[Mapping[str, Any]]:
        import pymongo  # noqa: PLC0415 - the driver is the deployment's

        client = pymongo.MongoClient(self._uri, serverSelectionTimeoutMS=10_000)
        try:
            found = client[self._database][collection].find(
                {"document_id": {"$regex": document_regex, "$options": "i"}}
            )
            return [dict(document) for document in found]
        finally:
            client.close()


# =========================================================================
# ACQUIRE — the envelope first, then the estate it admits
# =========================================================================


def acquire(
    *,
    alert_id: str,
    asked_at: datetime,
    as_of: datetime,
    network_depth: int,
    perspective: str,
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

    # 1. THE DEPARTMENTAL READ, BEFORE ANY ENTERPRISE SOURCE. Which SARs this
    #    perspective may even know exist.
    sars = _visible_sars(control_room, terms, alert_id=alert_id, perspective=perspective)

    # 2. The perspective's plan — its ceiling on what is assembled.
    plan = plan_for(relational, perspective=perspective, table=tables["projection_plan"])
    if plan is None:
        raise NoPlanForPerspective(
            f"perspective `{perspective}` has no row in `{tables['projection_plan']}`"
        )

    # 3. The alert. No row -> an EMPTY estate, never a raise (the A6 comparator).
    alerts = relational.rows(
        f"select alert_id, subject_party, raised_at, trigger, case_id"
        f" from {tables['alert']} where alert_id = %s",
        (alert_id,),
    )
    if not alerts:
        return Estate(alert_id=alert_id, perspective=perspective, plan=plan, posture=None,
                      permitted=(), alert=None, records=(), ledger_t=graph.watermark())
    alert = {key: "" if value is None else str(value) for key, value in alerts[0].items()}

    # 4. The typologies the subject party matches, and the posture at `as_of`.
    typologies = _typologies_for(graph, terms, party_id=alert["subject_party"])
    posture = posture_at(graph, terms, at=as_of.date())
    permitted = permitted_dispositions(graph, terms, posture=posture, typologies=typologies)

    # 5. The residency entitlement this perspective's principal holds.
    entitled_to_eu = _residency_entitlement(relational, terms, perspective=perspective)

    records = _records(
        relational, graph, documents, terms,
        alert=alert, plan=plan, typologies=typologies, sars=sars,
        network_depth=network_depth, asked_at=asked_at, entitled_to_eu=entitled_to_eu,
    )
    return Estate(
        alert_id=alert_id, perspective=perspective, plan=plan, posture=posture,
        permitted=permitted, alert=alert, records=records,
        ledger_t=graph.watermark(), typologies=typologies,
    )


def _visible_sars(
    control_room: _ControlRoom, terms: Mapping[str, Any], *, alert_id: str, perspective: str
) -> tuple[Mapping[str, str], ...]:
    """The SARs this perspective may know exist. The rest are never minted."""
    room = terms["control_room"]
    rows = control_room.sar_rows(table=room["table"], columns=room["columns"], alert_id=alert_id)
    visible: list[Mapping[str, str]] = []
    for row in rows:
        try:
            audience = json.loads(row[room["columns"]["visible_to"]] or "[]")
        except ValueError:  # pragma: no cover - a malformed row is not visible
            audience = []
        if perspective in audience:
            visible.append(row)
    return tuple(visible)


def plan_for(relational: _Relational, *, perspective: str, table: str) -> Plan | None:
    """The perspective's own projection plan, or `None`."""
    rows = relational.rows(
        f"select perspective, elements from {table} where perspective = %s", (perspective,)
    )
    if not rows:
        return None
    elements = rows[0]["elements"] or []
    return Plan(perspective=perspective, elements=tuple(str(e) for e in elements))


def planned_perspectives(*, relational_settings: Mapping[str, str]) -> tuple[str, ...]:
    """Every perspective the estate holds a plan for."""
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    table = vocabulary()["relational"]["tables"]["projection_plan"]
    return tuple(str(row["perspective"]) for row in relational.rows(f"select perspective from {table} order by 1"))


def required_classes(plan: Plan, terms: Mapping[str, Any]) -> tuple[str, ...]:
    """The classes this perspective needs for completeness (`C`)."""
    by_element = {
        "alert_core_facts": "alert",
        "typology_pattern_summary": "typology_match",
        "disposition_candidates": "alert",
        "sanctions_screening_result": "screening_result",
        "counterparty_network": "party",
        "ownership_chain": "party",
        "prior_alert_lineage": "prior_alert",
        "sar_filing_history": "sar_record",
        "policy_version_attribution": "alert",
        "reasoning_trail": "advisory_passage",
    }
    del terms
    return tuple(sorted({by_element[element] for element in plan.elements if element in by_element}))


def posture_at(graph: _Graph, terms: Mapping[str, Any], *, at: date) -> Posture | None:
    """The filing posture with the greatest effective date at or before `at`."""
    predicates = terms["graph"]["predicates"]
    prefix = terms["graph"]["prefix"]
    rows = graph.select(
        f"SELECT ?posture ?from FROM <LEDGER> WHERE {{"
        f" ?posture a <{prefix}{terms['graph']['types']['filing_posture']}> ;"
        f" <{predicates['posture_effective_from']}> ?from . }}"
    )
    effective: list[Posture] = []
    for row in rows:
        stamp = _as_date(row.get("from"))
        if stamp is not None and stamp <= at:
            effective.append(Posture(posture_id=str(row["posture"]).rsplit("/", 1)[-1],
                                     effective_from=stamp.isoformat()))
    if not effective:
        return None
    return sorted(effective, key=lambda posture: posture.effective_from)[-1]


def permitted_dispositions(
    graph: _Graph, terms: Mapping[str, Any], *, posture: Posture | None, typologies: Sequence[str]
) -> tuple[str, ...]:
    """The dispositions this posture permits for these typologies.

    THE BOUND, computed before any candidate exists. No posture in force means
    an EMPTY permitted set, and an empty set means no candidate is generated —
    not generated and rejected.
    """
    if posture is None or not typologies:
        return ()
    predicates = terms["graph"]["predicates"]
    prefix = terms["graph"]["prefix"]
    pattern = re.compile(terms["graph"]["rule_id_pattern"])
    rows = graph.select(
        f"SELECT ?rule ?permitted FROM <LEDGER> WHERE {{"
        f" ?rule a <{prefix}{terms['graph']['types']['disposition_rule']}> ;"
        f" <{predicates['permits_disposition']}> ?permitted . }}"
    )
    permitted: set[str] = set()
    for row in rows:
        match = pattern.match(str(row["rule"]).rsplit("/", 1)[-1])
        if match is None or match.group("posture") != posture.posture_id:
            continue
        if match.group("typology") not in typologies:
            continue
        if str(row.get("permitted", "")).lower() == "true":
            permitted.add(match.group("disposition"))
    return tuple(sorted(permitted))


def _typologies_for(graph: _Graph, terms: Mapping[str, Any], *, party_id: str) -> tuple[str, ...]:
    predicates = terms["graph"]["predicates"]
    rows = graph.select(
        f"SELECT ?typology FROM <LEDGER> WHERE {{"
        f" <{terms['graph']['prefix']}{party_id}> <{predicates['matches_typology']}> ?typology . }}"
    )
    return tuple(sorted({str(row["typology"]).rsplit("/", 1)[-1] for row in rows}))


def _residency_entitlement(
    relational: _Relational, terms: Mapping[str, Any], *, perspective: str
) -> bool:
    """Whether this perspective's principal holds the declared entitlement.

    The constraint names countries in full, parties carry ISO3 and principals
    carry ISO2 prefixes (`ATM-F-02`). The binding evaluates the DECLARED
    ENTITLEMENT and invents no country mapping: an AML perspective holds it
    only if a principal carrying it maps to this perspective, and this
    deployment maps none, so the flag is read and reported rather than assumed.
    """
    column = terms["residency"]["entitlement_column"]
    table = terms["relational"]["tables"]["principal"]
    rows = relational.rows(f"select {column} from {table} where perspective = %s", (perspective,))
    return bool(rows and rows[0][column])


def _records(
    relational: _Relational, graph: _Graph, documents: _Documents, terms: Mapping[str, Any], *,
    alert: Mapping[str, str], plan: Plan, typologies: Sequence[str],
    sars: Sequence[Mapping[str, str]], network_depth: int, asked_at: datetime,
    entitled_to_eu: bool,
) -> tuple[Record, ...]:
    """Every admissible claim, minted only if the envelope admits its class."""
    tables = terms["relational"]["tables"]
    prefixes = terms["entity_uri_prefix"]
    assignment = terms["classification"]["assignment"]
    elements = set(plan.elements)
    records: list[Record] = []

    def keep(element: str) -> bool:
        return element in elements

    # The subject party and, to `network_depth`, its counterparties.
    if keep("counterparty_network") or keep("ownership_chain") or keep("alert_core_facts"):
        parties = _network(relational, graph, terms, subject=alert["subject_party"], depth=network_depth)
        for party_id, hops in parties:
            rows = relational.rows(
                f"select party_id, legal_name, jurisdiction, party_kind from {tables['party']}"
                f" where party_id = %s", (party_id,),
            )
            if not rows:
                continue
            row = {k: "" if v is None else str(v) for k, v in rows[0].items()}
            # The residency bound: constrained-resident detail requires the
            # declared entitlement, and without it the party is not minted.
            if not entitled_to_eu and _eu_resident(row.get("jurisdiction", "")):
                continue
            records.append(Record(
                entity_class="party",
                edge_type="hasSubjectParty" if hops == 0 else "hasCounterparty",
                entity_uri=f"{prefixes['party']}{party_id}",
                attributes={**row, "hops": str(hops), "classification": assignment["party"]},
                dated=None,
            ))

    if keep("alert_core_facts"):
        for row in relational.rows(
            f"select txn_id, from_party, to_party, amount_usd, value_date, channel"
            f" from {tables['transaction']} where from_party = %s or to_party = %s"
            f" order by value_date desc limit 40",
            (alert["subject_party"], alert["subject_party"]),
        ):
            attributes = {k: "" if v is None else str(v) for k, v in row.items()}
            records.append(Record(
                entity_class="transaction", edge_type="hasTransaction",
                entity_uri=f"{prefixes['transaction']}{attributes['txn_id']}",
                attributes={**attributes, "classification": assignment["transaction"]},
                dated=_as_date(attributes["value_date"]),
            ))

    if keep("typology_pattern_summary"):
        for typology_id in typologies:
            records.append(Record(
                entity_class="typology_match", edge_type="hasTypologyMatch",
                entity_uri=f"{prefixes['typology_match']}{typology_id}",
                attributes={"typology_id": typology_id, "label": typology_id,
                            "confidence": "0.80", "classification": assignment["typology_match"]},
                dated=None,
            ))

    if keep("reasoning_trail") or keep("typology_pattern_summary"):
        for passage in _advisories(documents, terms, typologies=typologies):
            records.append(Record(
                entity_class="advisory_passage", edge_type="hasAdvisory",
                entity_uri=f"{prefixes['advisory_passage']}{passage['passage_id']}",
                attributes={**passage, "classification": assignment["advisory_passage"]},
                dated=None,
            ))

    if keep("prior_alert_lineage"):
        for row in relational.rows(
            f"select l.related_alert_id, l.relation, a.raised_at from {tables['alert_link']} l"
            f" join {tables['alert']} a on a.alert_id = l.related_alert_id"
            f" where l.alert_id = %s", (alert["alert_id"],),
        ):
            attributes = {k: "" if v is None else str(v) for k, v in row.items()}
            records.append(Record(
                entity_class="prior_alert", edge_type="hasPriorAlert",
                entity_uri=f"{prefixes['prior_alert']}{attributes['related_alert_id']}",
                attributes={"alert_id": attributes["related_alert_id"],
                            "relation": attributes["relation"],
                            "raised_at": attributes["raised_at"],
                            "classification": assignment["prior_alert"]},
                dated=_as_date(attributes["raised_at"]),
            ))

    if keep("sanctions_screening_result"):
        for row in relational.rows(
            f"select person_key, listed_name, score, disposition from {tables['screening_result']}"
            f" where person_key = %s", (alert["subject_party"],),
        ):
            attributes = {k: "" if v is None else str(v) for k, v in row.items()}
            records.append(Record(
                entity_class="screening_result", edge_type="hasScreeningResult",
                entity_uri=f"{prefixes['screening_result']}{attributes['person_key']}",
                attributes={**attributes, "classification": assignment["screening_result"]},
                dated=None,
            ))

    # The SARs the departmental read already narrowed to this perspective.
    # A SAR outside it was never in `sars`, so no claim exists to remove.
    if keep("sar_filing_history"):
        room = terms["control_room"]["columns"]
        for sar in sars:
            records.append(Record(
                entity_class="sar_record", edge_type="hasSarRecord",
                entity_uri=f"{prefixes['sar_record']}{sar[room['sar_id']]}",
                attributes={"sar_id": sar[room["sar_id"]], "alert_id": sar[room["alert_id"]],
                            "classification": f"{terms['classification']['sar_prefix']}{sar[room['classification']]}"},
                dated=None,
            ))

    del asked_at
    return tuple(records)


def _network(
    relational: _Relational, graph: _Graph, terms: Mapping[str, Any], *, subject: str, depth: int
) -> list[tuple[str, int]]:
    """The subject and its counterparties to `depth` hops, breadth-first."""
    del graph
    tables = terms["relational"]["tables"]
    seen: dict[str, int] = {subject: 0}
    frontier = [subject]
    for hop in range(1, max(1, min(int(depth), 4)) + 1):
        if not frontier:
            break
        rows = relational.rows(
            f"select from_party, to_party from {tables['transaction']}"
            f" where from_party = any(%s) or to_party = any(%s)",
            (frontier, frontier),
        )
        nxt: list[str] = []
        for row in rows:
            for party in (row["from_party"], row["to_party"]):
                party = str(party)
                if party and party not in seen:
                    seen[party] = hop
                    nxt.append(party)
        frontier = nxt[:60]
    return sorted(seen.items(), key=lambda pair: (pair[1], pair[0]))


def _advisories(
    documents: _Documents, terms: Mapping[str, Any], *, typologies: Sequence[str]
) -> list[Mapping[str, str]]:
    """The advisory passages for the matched typologies, by their own field."""
    fields = terms["documents"]["fields"]
    wanted = {t.replace("TYP-", "").lower() for t in typologies}
    found: list[Mapping[str, str]] = []
    for passage in documents.passages(
        collection=terms["documents"]["collection"],
        document_regex=terms["documents"]["match"]["document_id_regex"],
    ):
        typology = str(passage.get(fields["typology"], "")).lower()
        if wanted and not any(token in typology for token in wanted):
            continue
        found.append({
            "passage_id": str(passage.get(fields["passage_id"], "")),
            "document_id": str(passage.get(fields["document_id"], "")),
            "advisory_number": str(passage.get(fields["advisory_number"], "")),
            "typology_id": str(passage.get(fields["typology"], "")),
            "text": str(passage.get(fields["text"], ""))[:600],
        })
    return found


def _eu_resident(jurisdiction: str) -> bool:
    """Whether an ISO3 jurisdiction is inside the constrained set.

    The constraint's own country list is prose and the parties are ISO3
    (`ATM-F-02`); this deployment states the ISO3 set it treats as
    constrained rather than deriving one from the prose, and says so.
    """
    return jurisdiction.upper() in _EU_ISO3


_EU_ISO3 = frozenset({
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU",
    "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT",
    "ROU", "SVK", "SVN", "ESP", "SWE", "ISL", "LIE", "NOR",
})


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
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
