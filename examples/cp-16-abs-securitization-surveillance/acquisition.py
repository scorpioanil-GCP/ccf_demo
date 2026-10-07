"""The estate half of `cib.abs-surveillance` — three stores, one order.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's: it takes
settings by name, returns dated claims, and never touches a Control Plane, a
product or a door.

THE ORDER IS THE POINT (`CP-SPEC-016` §D.3). The granularity ceiling is
resolved FIRST, from the caller's verified role, because a loan record above
the ceiling must never be materialized — not filtered afterwards, never minted.
Only then is the reporting period resolved, then the structure, then the
trigger definitions in force, then the performance rows at the EFFECTIVE
granularity.

TWO THINGS THIS MODULE MEASURES RATHER THAN ASSERTS (`CP-SPEC-016` §0.2b):

- ``records_materialized`` — how many rows became claims. This is the number
  the load-bearing property is about: the product must not materialize a
  1.3-million-row population to answer a question about four cohorts.
- ``blocks_scanned`` — how many shared buffers the statement touched, read by
  explaining the same statement. Rows and blocks answer *different* questions
  and neither substitutes for the other: a prefix `LIMIT` materializes few rows
  for few blocks and is unrepresentative, while a representative sample
  materializes few rows and still scans the partition. Measured 2026-09-21;
  see `FINDINGS.md` (`ABS-F-01`).

Cost is never measured in TIME here. The estate's own 24 timed runs put
`cohort`'s median between 0.148 ms and 205.871 ms on identical data while its
block count never moved off 2 (`CP-SPEC-016` §A.2).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"
PERSPECTIVES = HERE / "artifacts" / "perspectives.yaml"

#: The maximum loan rows this product will ever MATERIALIZE as claims.
MAX_LOAN_SAMPLE = 5000


class CeilingExceeded(ValueError):
    """The caller asked for a granularity above its role's ceiling."""

    def __init__(self, *, requested: str, ceiling: str, allowed: Sequence[str], role: str) -> None:
        self.requested, self.ceiling, self.allowed, self.role = requested, ceiling, tuple(allowed), role
        super().__init__(
            f"granularity `{requested}` is not in the allowed set {list(allowed)} for role"
            f" `{role}`, whose ceiling is `{ceiling}`"
        )


class UnboundedLoanRequest(ValueError):
    """Loan granularity was asked for with no bound on what may be materialized."""


class UnpricedIntent(ValueError):
    """The caller named an intent this product prices no envelope for."""


class UnknownGranularity(ValueError):
    """The caller named a granularity outside the declared domain."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    """Every source name this deployment reads, from its declared artifact."""
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def perspectives() -> Mapping[str, Any]:
    """The declared roles, their ceilings, and the granularity ordering."""
    return yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]


def granularity_order() -> tuple[str, ...]:
    return tuple(perspectives()["granularity_order"])


def required_classes() -> tuple[str, ...]:
    """The classes a complete product at the FULL granularity would carry."""
    return ("deal", "tranche", "trigger", "anchor", "cohort", "benchmark", "repurchase")


# =========================================================================
# THE ENVELOPE — the granularity ceiling, resolved first
# =========================================================================


@dataclass(frozen=True)
class Ceiling:
    """What granularity the verified role may ask for, and on whose authority.

    `authority` is the Control Plane artifact that BOUND the request.
    `estate_value` is what `abs_granularity_entitlement` independently declares
    for the same role. `ABS-G11` asserts the two agree — two authorities that
    can drift are checked against each other rather than allowed to disagree
    silently (`CP-SPEC-016` §C.3 trap 5).
    """

    role: str
    ceiling: str
    authority: str
    estate_value: str | None
    allowed: tuple[str, ...]

    @property
    def agrees_with_estate(self) -> bool:
        return self.estate_value is None or self.estate_value == self.ceiling


@dataclass(frozen=True)
class Scan:
    """What one leg of the acquisition actually touched."""

    leg: str
    records_scanned: int
    records_materialized: int
    blocks_scanned: int


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

    deal_id: str
    perspective: str
    ceiling: Ceiling | None
    requested_granularity: str
    effective_granularity: str
    deal: Mapping[str, str] | None
    period: str
    records: tuple[Record, ...]
    scans: tuple[Scan, ...]
    ledger_t: str
    cost_reference: tuple[Mapping[str, Any], ...] = ()
    findings: tuple[Mapping[str, str], ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return self.deal is None

    @property
    def records_materialized(self) -> int:
        return sum(scan.records_materialized for scan in self.scans)

    @property
    def records_scanned(self) -> int:
        return sum(scan.records_scanned for scan in self.scans)

    @property
    def blocks_scanned(self) -> int:
        return sum(scan.blocks_scanned for scan in self.scans)


# =========================================================================
# THE READERS
# =========================================================================


class _Relational:
    """PostgreSQL, read-only, by DSN and schema name — and it counts blocks."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def _connect(self) -> Any:
        import psycopg  # noqa: PLC0415

        return psycopg.connect(self._dsn, autocommit=True)

    def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        from psycopg.rows import dict_row  # noqa: PLC0415
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            return [dict(row) for row in cursor.fetchall()]

    def rows_and_cost(
        self, *, leg: str, sql: str, args: tuple[Any, ...] = ()
    ) -> tuple[list[Mapping[str, Any]], Scan]:
        """The rows, and what the statement cost in rows scanned and blocks.

        The block figure is read by EXPLAIN-ing the SAME statement, which is how
        `ccf-dataprep` measured the published curve. It is the statement's own
        cost rather than a second, unrelated number — and it is disclosed in the
        README because explaining a statement runs it.
        """
        from psycopg.rows import dict_row  # noqa: PLC0415
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            fetched = [dict(row) for row in cursor.fetchall()]
            scanned, blocks = _explain(cursor, sql, args)
        return fetched, Scan(leg=leg, records_scanned=scanned,
                             records_materialized=len(fetched), blocks_scanned=blocks)


def _explain(cursor: Any, sql: str, args: tuple[Any, ...]) -> tuple[int, int]:
    """Rows actually scanned and shared blocks touched, from the plan itself."""
    cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", args)  # noqa: S608
    row = cursor.fetchone()
    plan = (list(row.values())[0] if isinstance(row, dict) else row[0])[0]["Plan"]
    totals = {"rows": 0, "blocks": 0}

    def walk(node: Mapping[str, Any]) -> None:
        totals["blocks"] += int(node.get("Shared Hit Blocks", 0)) + int(node.get("Shared Read Blocks", 0))
        if not node.get("Plans"):
            totals["rows"] += int(node.get("Actual Rows", 0))
        for child in node.get("Plans", ()):
            walk(child)

    walk(plan)
    return max(totals["rows"], int(plan.get("Actual Rows", 0))), totals["blocks"]


#: An absolute IRI as SPARQL 1.1 lets it stand between `<` and `>`: a scheme,
#: then nothing `IRIREF` excludes — `<>"{}|^`, a backtick, a backslash, or any
#: character up to U+0020. Matched WHOLE, so a trailing newline cannot slip
#: past an end-of-line anchor. A deal IRI carries the caller's deal id, and the
#: trigger read runs before the deal-existence check (`EX-01`).
_IRI = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*:[^<>"{}|^`\\\x00-\x20]*')


def _iri(value: str) -> str:
    """`value` if it can stand in a SPARQL `<…>` position; refused before any read."""
    if not _IRI.fullmatch(value):
        raise ValueError(f"{value!r} is not an IRI and cannot be placed in a SPARQL <…> position")
    return value


class _Graph:
    """Fluree — the trigger definitions, their supersession, and the watermark."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def _query(self, sparql: str) -> tuple[list[Mapping[str, str]], str]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query", data=sparql.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                payload = json.loads(response.read())
                watermark = str(response.headers.get("x-fdb-t") or "unreported")
        except (urllib.error.URLError, TimeoutError):  # pragma: no cover - environment
            return [], "unreported"
        bindings = payload.get("results", {}).get("bindings", [])
        return [{key: value["value"] for key, value in row.items()} for row in bindings], watermark

    def triggers(self, *, deal_uri: str) -> tuple[list[Mapping[str, str]], str]:
        """Every trigger definition reachable from the deal, ORIGINALS AND AMENDMENTS.

        The amendment is reached by `specifiesTrigger` then `supersededBy` —
        the estate's own two-hop structure. NO name-match join is invented, and
        `ABS-G04` reddens if one is substituted (`CP-SPEC-016` §D.3).
        """
        terms = vocabulary()["graph"]
        superseded = f"{terms['ex']}{terms['predicates']['superseded_by']}"
        return self._query(f"""SELECT ?t ?p ?o ?origin FROM <{self._ledger}> WHERE {{
  <{_iri(deal_uri)}> <{terms['specifies_trigger']}> ?orig .
  {{ ?orig ?p ?o . BIND(?orig AS ?t) BIND("declared" AS ?origin) }}
  UNION
  {{ ?orig <{superseded}> ?amd . ?amd ?p ?o . BIND(?amd AS ?t) BIND(STR(?orig) AS ?origin) }}
}}""")


class _Documents:
    """MongoDB — the filed prospectus spans each threshold is anchored to."""

    def __init__(self, *, uri: str, database: str) -> None:
        self._uri, self._database = uri, database

    def anchors(self, *, collection: str, deal_id: str) -> list[Mapping[str, Any]]:
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(self._uri, serverSelectionTimeoutMS=15000)
        try:
            return [dict(doc) for doc in client[self._database][collection].find({"deal_id": deal_id})]
        finally:
            client.close()

    def passage_hashes(self, *, collection: str, passage_ids: Sequence[str]) -> Mapping[str, str]:
        """`passage_id` -> stored `sha256`, so `ABS-G06` can re-hash the span."""
        if not passage_ids:
            return {}
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(self._uri, serverSelectionTimeoutMS=15000)
        try:
            found = client[self._database][collection].find(
                {"passage_id": {"$in": list(passage_ids)}}, {"passage_id": 1, "sha256": 1}
            )
            return {str(doc["passage_id"]): str(doc.get("sha256", "")) for doc in found}
        finally:
            client.close()


# =========================================================================
# THE CEILING
# =========================================================================


def ceiling_for(relational: _Relational, *, role: str, tables: Mapping[str, str]) -> Ceiling:
    """What this role may ask for — declared here, cross-checked against the estate."""
    declared = perspectives()["perspectives"].get(role)
    if declared is None:
        raise UnpricedIntent(f"role `{role}` is not declared in `artifacts/perspectives.yaml`")
    ceiling = str(declared["ceiling"])
    order = granularity_order()
    allowed = order[: order.index(ceiling) + 1]
    rows = relational.rows(
        f"select max_granularity from {tables['granularity_entitlement']} where principal = %s",  # noqa: S608
        (role,),
    )
    estate_value = str(rows[0]["max_granularity"]) if rows else None
    return Ceiling(role=role, ceiling=ceiling, authority="cp-16.perspectives",
                   estate_value=estate_value, allowed=allowed)


def bound_granularity(*, requested: str, ceiling: Ceiling) -> str:
    """The effective granularity — or a refusal by name. NEVER a silent lowering.

    `D-IMPL-251`: the constraint layer refuses an out-of-bound value and never
    narrows it. Route B and `ABS-G09` keep that: a request above the ceiling is
    refused `not-in-allowed-set` with the bound attached.
    """
    if requested not in granularity_order():
        raise UnknownGranularity(
            f"granularity `{requested}` is outside the declared domain {list(granularity_order())}"
        )
    if requested not in ceiling.allowed:
        raise CeilingExceeded(requested=requested, ceiling=ceiling.ceiling,
                              allowed=ceiling.allowed, role=ceiling.role)
    return requested


# =========================================================================
# ACQUIRE
# =========================================================================


def acquire(
    *,
    deal_id: str,
    asked_at: datetime,
    as_of: datetime,
    intent: str,
    perspective: str,
    requested_granularity: str,
    cohorts: Sequence[str],
    loan_sample: int,
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
    document_settings: Mapping[str, str],
) -> Estate:
    """Everything one question admits, in the one order that is safe."""
    del asked_at  # the decision instant is `as_of` (`CP-SPEC-016` §F.4.1)
    terms = vocabulary()
    tables = terms["relational"]["tables"]
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])
    documents = _Documents(uri=document_settings["uri"], database=document_settings["db"])

    if intent not in _PRICED_INTENTS:
        raise UnpricedIntent(
            f"this product prices no envelope for intent `{intent}`;"
            f" the priced intents are {list(_PRICED_INTENTS)}"
        )

    # 1. THE CEILING, FIRST. A loan row above it is never selected.
    ceiling = ceiling_for(relational, role=perspective, tables=tables)
    effective = bound_granularity(requested=requested_granularity, ceiling=ceiling)
    if effective == "loan" and loan_sample <= 0:
        raise UnboundedLoanRequest(
            "granularity `loan` requires a positive `loan_sample`; this product cannot be asked"
            " to materialize the whole pool"
        )
    sample = min(int(loan_sample), MAX_LOAN_SAMPLE)

    # 2. THE DECISION INSTANT bounds every read that follows.
    period = _period_of(as_of)
    records: list[Record] = []
    scans: list[Scan] = []
    findings: list[Mapping[str, str]] = []

    # 3. The anchor. No reporting period at `as_of` -> an EMPTY estate, never a
    #    raise: a deal that exists and a deal that does not must be
    #    indistinguishable on the vessel (`ABS-G22`).
    deal_rows, deal_scan = relational.rows_and_cost(
        leg="deal",
        sql=f"select d.*, r.period, r.pool_balance, r.note_balance, r.oc_amount, r.oc_target,"  # noqa: S608
            f" r.published_delinquency_percent, r.published_delinquency_trigger,"
            f" r.published_trigger_occurred, r.receivable_count, r.cumulative_net_loss_percent"
            f" from {tables['deal']} d join {tables['servicer_report']} r on r.deal_id = d.deal_id"
            f" where d.deal_id = %s and r.period = %s",
        args=(deal_id, period),
    )
    scans.append(deal_scan)
    _, watermark = graph.triggers(deal_uri=f"{terms['graph']['deal_uri_prefix']}{deal_id}")
    if not deal_rows:
        return Estate(deal_id=deal_id, perspective=perspective, ceiling=ceiling,
                      requested_granularity=requested_granularity, effective_granularity=effective,
                      deal=None, period=period, records=(), scans=tuple(scans), ledger_t=watermark)
    deal = deal_rows[0]

    # 4. STRUCTURE — tranches, at `tranche` and below.
    order = granularity_order()
    reach = order.index(effective)
    if reach >= order.index("tranche"):
        rows, scan = relational.rows_and_cost(
            leg="tranche",
            sql=f"select * from {tables['tranche']} where deal_id = %s order by seniority_rank, tranche_id",  # noqa: S608
            args=(deal_id,),
        )
        scans.append(scan)
        records.extend(_tranche_records(rows, terms=terms))

    # 5. TRIGGER DEFINITIONS IN FORCE AT `as_of`, with their anchors.
    trigger_records, trigger_findings = _triggers(
        graph, documents, deal_id=deal_id, as_of=as_of, terms=terms
    )
    records.extend(trigger_records)
    findings.extend(trigger_findings)
    # The graph and document legs materialize claims as surely as the
    # relational ones do. Their block counts are not measurable through those
    # engines, and are reported as 0 rather than guessed — `records_scanned`
    # and `records_materialized` stay complete either way.
    scans.append(Scan(leg="trigger", records_scanned=len(trigger_records),
                      records_materialized=len(trigger_records), blocks_scanned=0))

    # 6. PERFORMANCE at the EFFECTIVE granularity — this is the fan-out seam.
    if reach >= order.index("cohort"):
        sql = (f"select * from {tables['cohort']} where deal_id = %s and period = %s")  # noqa: S608
        args: tuple[Any, ...] = (deal_id, period)
        if cohorts:
            sql += " and credit_band = any(%s)"
            args = (*args, list(cohorts))
        rows, scan = relational.rows_and_cost(leg="cohort", sql=sql + " order by credit_band", args=args)
        scans.append(scan)
        records.extend(_cohort_records(rows, terms=terms))

    if reach >= order.index("loan"):
        loan_records, loan_scan, loan_finding = _loan_sample(
            relational, tables=tables, deal_id=deal_id, period=period, sample=sample, terms=terms
        )
        records.extend(loan_records)
        scans.append(loan_scan)
        findings.append(loan_finding)

    # 7. BENCHMARK and REPURCHASE — always, at every granularity.
    bench_rows, bench_scan = relational.rows_and_cost(
        leg="benchmark",
        sql=f"select * from {tables['benchmark']} where vintage = %s and period = %s",  # noqa: S608
        args=(deal["vintage"], period),
    )
    scans.append(bench_scan)
    records.extend(_benchmark_records(bench_rows, terms=terms))

    rep_rows, rep_scan = relational.rows_and_cost(
        leg="repurchase",
        # BOUNDED AT THE DECISION INSTANT, in the statement. A filing made
        # after the instant is never selected, not filtered afterwards
        # (residual 341-1, `ABS-G05`).
        sql=f"select * from {tables['repurchase']} where depositor_cik = %s"  # noqa: S608
            f" and filed_date <= %s order by filed_date desc",
        args=(deal["depositor_cik"], as_of.date()),
    )
    scans.append(rep_scan)
    records.extend(_repurchase_records(rep_rows, terms=terms))
    if rep_rows:
        findings.append({
            "finding": "repurchase-activity-is-depositor-scoped",
            "detail": (
                f"ABS-15G is filed per depositor, not per trust: all {len(rep_rows)} filings for"
                f" depositor CIK {deal['depositor_cik']} cover the shelf. Per-deal attribution is"
                f" not available from the filing, and no join to this deal is invented"
            ),
        })

    cost_reference = _cost_reference(relational, tables=tables, deal_id=deal_id)

    return Estate(
        deal_id=deal_id, perspective=perspective, ceiling=ceiling,
        requested_granularity=requested_granularity, effective_granularity=effective,
        deal=_deal_attributes(deal), period=period, records=tuple(records),
        scans=tuple(scans), ledger_t=watermark, cost_reference=cost_reference,
        findings=tuple(findings),
    )


_PRICED_INTENTS = ("trigger-monitoring", "holdings-review", "client-reporting")


# =========================================================================
# THE TRIGGER WALK — and Route B's marking
# =========================================================================


def _triggers(
    graph: _Graph, documents: _Documents, *, deal_id: str, as_of: datetime, terms: Mapping[str, Any]
) -> tuple[list[Record], list[Mapping[str, str]]]:
    """The definition IN FORCE at `as_of` for each trigger, with its anchor.

    ROUTE B (`CP-SPEC-016` §F.4, ruled 2026-09-21). A threshold with no filed
    prospectus passage is SERVED, carrying `anchored: false`, a source
    classification of `engineered`, and a finding naming the missing public
    anchor. Nothing here writes an empty anchor object, a null `passage_id` or
    a placeholder document id: the absence is stated, never encoded as a blank.
    """
    graph_terms = terms["graph"]
    bindings, _ = graph.triggers(deal_uri=f"{graph_terms['deal_uri_prefix']}{deal_id}")
    by_subject: dict[str, dict[str, Any]] = {}
    for row in bindings:
        subject = row["t"]
        node = by_subject.setdefault(subject, {"uri": subject, "origin": row.get("origin", "declared")})
        node.setdefault(_local(row["p"]), row["o"])
        if _local(row["p"]) == graph_terms["predicates"]["threshold_component"]:
            node.setdefault("_components", []).append(row["o"])

    anchors = {
        str(doc.get("trigger_id")): doc
        for doc in documents.anchors(collection=terms["documents"]["anchor_collection"], deal_id=deal_id)
    }
    hashes = documents.passage_hashes(
        collection=terms["documents"]["passage_collection"],
        passage_ids=[str(doc.get("passage_id")) for doc in anchors.values() if doc.get("passage_id")],
    )

    # Group by the trigger the definition is a version OF, then pick the one in
    # force at `as_of` — the latest `validFrom` not after the instant.
    families: dict[str, list[Mapping[str, Any]]] = {}
    for node in by_subject.values():
        family = node["origin"] if node["origin"] != "declared" else node["uri"]
        families.setdefault(family, []).append(node)

    records: list[Record] = []
    findings: list[Mapping[str, str]] = []
    cut = as_of.date()
    for family, versions in sorted(families.items()):
        eligible = [v for v in versions if _as_date(v.get("validFrom")) and _as_date(v["validFrom"]) <= cut]
        if not eligible:
            continue
        in_force = max(eligible, key=lambda v: _as_date(v["validFrom"]))
        in_force_from = _as_date(in_force["validFrom"])
        # ONLY versions this one actually replaced BY THIS INSTANT. A version
        # whose `validFrom` is later is not yet in force and is not named: at
        # an instant before the amendment, the product must not disclose that
        # an amendment is coming.
        superseded = [
            v["uri"] for v in versions
            if v["uri"] != in_force["uri"]
            and (_as_date(v.get("validFrom")) or cut) < in_force_from
        ]
        trigger_id = _local(in_force["uri"])
        anchor_key = str(in_force.get("passageAnchor") or "").removesuffix("-anchor")
        anchor = anchors.get(anchor_key) or anchors.get(trigger_id)
        provenance = str(in_force.get("provenance", ""))
        classification = terms["classification"]["by_provenance"].get(provenance, "internal")
        anchored = anchor is not None

        attributes: dict[str, str] = {
            "trigger_id": trigger_id,
            "label": str(in_force.get("http://www.w3.org/2000/01/rdf-schema#label")
                         or in_force.get("label", "")),
            "threshold_value": str(in_force.get("thresholdValue", "")),
            "threshold_unit": str(in_force.get("thresholdUnit", "")),
            "threshold_components": ",".join(sorted(in_force.get("_components", []))),
            "valid_from": str(in_force.get("validFrom", "")),
            "asserted_at": str(in_force.get("assertedAt", "")),
            "anchored": "true" if anchored else "false",
            "source_classification": classification,
            "supersedes": ",".join(sorted(_local(uri) for uri in superseded)),
            "classification": classification,
        }
        if anchored:
            # THE FILED SPAN IS ITS OWN CLAIM (`ABS-F-04`). Keeping it off the
            # trigger is what lets an unanchored threshold carry no
            # anchor-shaped field at all, which Route B requires.
            assert anchor is not None
            passage_id = str(anchor.get("passage_id", ""))
            records.append(Record(
                entity_class="anchor", edge_type="hasAnchor",
                entity_uri=f"{terms['entity_uri_prefix']['trigger']}{trigger_id}:anchor",
                attributes={
                    "anchor_id": anchor_key,
                    "trigger_id": trigger_id,
                    "anchor_text": str(anchor.get("quoted_text", "")),
                    "anchor_passage_id": passage_id,
                    "anchor_document_id": str(anchor.get("document_id", "")),
                    "anchor_sha256": hashes.get(passage_id, ""),
                    "start_offset": str(anchor.get("start_offset", "")),
                    "end_offset": str(anchor.get("end_offset", "")),
                    "complete_span": str(anchor.get("complete_span", "")).lower(),
                    "classification": "public",
                },
                dated=None,
            ))
        else:
            # NOTHING is written for the anchor keys. A null or empty
            # `anchor_passage_id` would imply a passage that does not exist.
            findings.append({
                "finding": "threshold-has-no-public-anchor",
                "trigger_id": trigger_id,
                "detail": (
                    f"threshold `{trigger_id}` is in force at this instant and carries no filed"
                    f" prospectus passage; it is classified `{classification}` and served"
                    f" unanchored rather than refused or dropped (CP-SPEC-016 §F.4, Route B)"
                ),
            })
        if not str(in_force.get("thresholdValue", "")):
            findings.append({
                "finding": "threshold-is-not-a-number",
                "trigger_id": trigger_id,
                "detail": (
                    f"threshold `{trigger_id}` is defined as a formula in unit"
                    f" `{in_force.get('thresholdUnit', '')}` and carries no numeric value;"
                    f" proximity is uncomputable and is not reported as zero"
                ),
            })
        records.append(Record(
            entity_class="trigger", edge_type="hasTrigger",
            entity_uri=f"{terms['entity_uri_prefix']['trigger']}{trigger_id}",
            attributes=attributes, dated=None,
        ))
    return records, findings


# =========================================================================
# THE FAN-OUT SEAM
# =========================================================================


def _loan_sample(
    relational: _Relational, *, tables: Mapping[str, str], deal_id: str, period: str,
    sample: int, terms: Mapping[str, Any],
) -> tuple[list[Record], Scan, Mapping[str, str]]:
    """A representative loan sample, bounded, with the restricted fields absent.

    THE SAMPLE IS NOT A PREFIX. ABS-EE files are ordered in ways that make a
    prefix unrepresentative, and the measured cost says the same thing from the
    other side: a prefix `LIMIT` touches 16 blocks and a representative sample
    touches the partition's 1,849 — the cheap option is the one the source
    specification forbids (`FINDINGS.md`, `ABS-F-01`).

    IT IS NOT STRATIFIED BY CREDIT BAND EITHER, and that is a governed
    consequence rather than a shortcut: `credit_band` derives from
    `obligor_credit_score`, one of the four fields the estate's own
    `ex:LoanLevelPrivacyConstraint` nodes restrict to `cohort` granularity. A
    band-stratified loan sample would disclose a score bucket per loan
    (`ABS-F-02`). The sample is therefore uniform over the partition by a
    deterministic hash of the asset number — representative in expectation,
    stable across runs, and carrying none of the four restricted fields.
    """
    population = relational.rows(
        f"select count(*) as n from {tables['loan']} where deal_id = %s and period = %s",  # noqa: S608
        (deal_id, period),
    )
    total = int(population[0]["n"]) if population else 0
    stride = max(1, total // max(sample, 1))
    rows, scan = relational.rows_and_cost(
        leg="loan",
        sql=f"select asset_number, period, reporting_period_ending_date, original_loan_amount,"  # noqa: S608
            f" reporting_period_actual_end_balance_amount, current_delinquency_status,"
            f" chargedoff_principal_amount, recovered_amount"
            f" from {tables['loan']} where deal_id = %s and period = %s"
            f" and (abs(hashtext(asset_number)) %% %s) = 0 order by asset_number limit %s",
        args=(deal_id, period, stride, sample),
    )
    records = [
        Record(
            entity_class="loan", edge_type="hasLoan",
            entity_uri=f"{terms['entity_uri_prefix']['loan']}{row['asset_number']}@{row['period']}",
            attributes={
                "asset_number": str(row["asset_number"]),
                "period": str(row["period"]),
                "reporting_period_ending_date": str(row["reporting_period_ending_date"]),
                "original_loan_amount": str(row["original_loan_amount"]),
                "reporting_period_actual_end_balance_amount": str(
                    row["reporting_period_actual_end_balance_amount"]),
                "current_delinquency_status": str(row["current_delinquency_status"]),
                "chargedoff_principal_amount": str(row["chargedoff_principal_amount"]),
                "recovered_amount": str(row["recovered_amount"]),
                "classification": terms["classification"]["assignment"]["loan"],
            },
            dated=_as_date(row["reporting_period_ending_date"]),
        )
        for row in rows
    ]
    finding = {
        "finding": "loan-sample-is-uniform-not-band-stratified",
        "detail": (
            f"{len(records)} of {total} loan records materialized, sampled uniformly by a"
            f" deterministic hash rather than stratified by credit band, because the"
            f" stratification key derives from a field the estate restricts to cohort"
            f" granularity. The four restricted fields are absent from every loan record"
        ),
    }
    return records, scan, finding


def _cost_reference(
    relational: _Relational, *, tables: Mapping[str, str], deal_id: str
) -> tuple[Mapping[str, Any], ...]:
    """The estate's own published cost curve, carried as STAMPED EVIDENCE.

    These are not thresholds and nothing is compared against them: they are a
    dated measurement another party made, offered so a consumer can reason
    about the consequence of asking for more detail (`CP-SPEC-016` §A.2).
    """
    rows = relational.rows(
        f"select granularity, rows_returned, shared_blocks_accessed, row_basis,"  # noqa: S608
        f" min(measured_at) over () as measured_from, max(measured_at) over () as measured_to"
        f" from {tables['cost_measurement']} where deal_id = %s", (deal_id,),
    )
    by_granularity: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = by_granularity.setdefault(str(row["granularity"]), {
            "granularity": str(row["granularity"]),
            "rows_returned": int(row["rows_returned"]),
            "shared_blocks_accessed": int(row["shared_blocks_accessed"]),
            "row_basis": int(row["row_basis"]),
            "runs": 0,
            "measured_at": str(row["measured_from"])[:10],
        })
        entry["runs"] += 1
    order = granularity_order()
    return tuple(sorted(by_granularity.values(), key=lambda e: order.index(e["granularity"])))


# =========================================================================
# RECORD BUILDERS
# =========================================================================


def _tranche_records(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="tranche", edge_type="hasTranche",
               entity_uri=f"{terms['entity_uri_prefix']['tranche']}{row['tranche_id']}",
               attributes={
                   "tranche_id": str(row["tranche_id"]),
                   "class_name": str(row["class_name"]),
                   "seniority_rank": str(row["seniority_rank"]),
                   "cusip": str(row["cusip"] or ""),
                   "interest_rate": str(row["interest_rate"] if row["interest_rate"] is not None else ""),
                   "interest_rate_basis": str(row["interest_rate_basis"]),
                   "classification": terms["classification"]["assignment"]["tranche"],
               }, dated=None)
        for row in rows
    ]


def _cohort_records(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="cohort", edge_type="hasCohort",
               entity_uri=f"{terms['entity_uri_prefix']['cohort']}{row['deal_id']}:{row['period']}:{row['credit_band']}",
               attributes={
                   "credit_band": str(row["credit_band"]),
                   "period": str(row["period"]),
                   "loan_count": str(row["loan_count"]),
                   "pool_balance": str(row["pool_balance"]),
                   "delinquent_60_plus_balance": str(row["delinquent_60_plus_balance"]),
                   "delinquency_percent": str(row["delinquency_percent"]),
                   "chargedoff_amount": str(row["chargedoff_amount"]),
                   "recovered_amount": str(row["recovered_amount"]),
                   "weighted_average_coupon_percent": str(row["weighted_average_coupon_percent"]),
                   "classification": terms["classification"]["assignment"]["cohort"],
               }, dated=_period_end(str(row["period"])))
        for row in rows
    ]


def _benchmark_records(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="benchmark", edge_type="hasBenchmark",
               entity_uri=f"{terms['entity_uri_prefix']['benchmark']}{row['asset_class']}:{row['vintage']}:{row['period']}",
               attributes={
                   "asset_class": str(row["asset_class"]),
                   "vintage": str(row["vintage"]),
                   "period": str(row["period"]),
                   "credit_tiers": str(row["credit_tiers"]),
                   "deal_count": str(row["deal_count"]),
                   "pool_balance": str(row["pool_balance"]),
                   "delinquency_percent": str(row["delinquency_percent"]),
                   "period_chargeoff_percent": str(row["period_chargeoff_percent"]),
                   "classification": terms["classification"]["assignment"]["benchmark"],
               }, dated=_period_end(str(row["period"])))
        for row in rows
    ]


def _repurchase_records(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="repurchase", edge_type="hasRepurchase",
               entity_uri=f"{terms['entity_uri_prefix']['repurchase']}{row['repurchase_id']}",
               attributes={
                   "repurchase_id": str(row["repurchase_id"]),
                   "depositor_cik": str(row["depositor_cik"]),
                   "form": str(row["form"]),
                   "accession": str(row["accession"]),
                   "filed_date": str(row["filed_date"]),
                   # The estate's `deal_id` is NULL on every row, and that is
                   # the fact rather than a gap (`ABS-G18`).
                   "deal_attributed": "false" if row["deal_id"] is None else "true",
                   "note": str(row["note"] or ""),
                   "classification": terms["classification"]["assignment"]["repurchase"],
               }, dated=_as_date(row["filed_date"]))
        for row in rows
    ]


def _deal_attributes(row: Mapping[str, Any]) -> Mapping[str, str]:
    keys = ("deal_id", "legal_name", "cik", "depositor_cik", "credit_tier", "vintage", "servicer",
            "period", "pool_balance", "note_balance", "oc_amount", "oc_target",
            "published_delinquency_percent", "published_delinquency_trigger",
            "published_trigger_occurred", "receivable_count", "cumulative_net_loss_percent")
    return {key: str(row[key]) for key in keys if row.get(key) is not None}


# --- helpers ------------------------------------------------------------------------


def _local(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _period_of(instant: datetime) -> str:
    return f"{instant.year:04d}-{instant.month:02d}"


def _period_end(period: str) -> date | None:
    try:
        year, month = (int(part) for part in period.strip().split("-"))
    except (ValueError, TypeError):
        return None
    if month == 12:
        return date(year, 12, 31)
    return date.fromordinal(date(year, month + 1, 1).toordinal() - 1)


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
