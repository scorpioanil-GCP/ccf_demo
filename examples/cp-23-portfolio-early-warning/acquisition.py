"""The estate half of `cib.portfolio-early-warning` — one book, many members.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's.

THE ASSEMBLY UNIT IS A POPULATION (`CP-SPEC-023` §0.2a). Every earlier rung
anchored on one thing; here the members *are* the answer, and the reads are
batched per limb over the whole population rather than looped per member.

THE ORDER IS THE POINT. The caller's role is resolved FIRST, because it decides
which members and which measures may be assembled at all — a member a role may
not see is never selected, not filtered afterwards.

MEMBERSHIP IS A STANDING STATE, NOT A DATED EVENT (`D-IMPL-332`). A book is *as
it stands*: `coverage_assignment` carries an `assigned_date` and no end date, so
this product does not claim to reconstruct a historical book. The signals are
dated events and carry their day.
"""

from __future__ import annotations

import hashlib
import json
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
TIERS = HERE / "artifacts" / "severity-tiers.yaml"


class NotInBook(ValueError):
    """The caller named a member that is not in this book."""


class UnpricedIntent(ValueError):
    """The caller named an intent this product prices no envelope for."""


class FloorLowered(ValueError):
    """The caller asked for a severity floor below the declared one."""


class UnknownRole(ValueError):
    """The caller's role is not declared in `artifacts/perspectives.yaml`."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def perspectives() -> Mapping[str, Any]:
    return yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def tiers() -> Mapping[str, Any]:
    return yaml.safe_load(TIERS.read_text(encoding="utf-8"))["declaration"]


def signal_classes() -> Mapping[str, str]:
    """`signal_type` -> the entity class whose `λ_c` governs it."""
    return vocabulary()["signal_classes"]


def required_classes() -> tuple[str, ...]:
    """The classes a complete book would carry."""
    return ("book", "member", "facility", "covenant", *sorted(signal_classes().values()))


# =========================================================================
# THE MEMBER SET — canonicalized by the DEPLOYMENT, because it is a SET
# =========================================================================


def canonical_members(members: Sequence[str] | None) -> tuple[str, ...]:
    """Deduplicate and sort — the deployment's canonicalization (`Q2`, ruled).

    CP-23 knows its portfolio membership is **semantically a set**, so the
    deployment owns this rather than the SDK: a `ProductRequest` carrying
    `["A","B","C"]` and one carrying `["C","B","A"]` canonicalize to the same
    tuple, so they build the SAME effective request and hash to the same
    content address (`PEW-G05`). A genuinely different membership still
    produces a different one (`PEW-G06`).

    **SDK list canonicalization is NOT changed globally** — that would reach
    every rung, and array order is legitimately identity for a parameter whose
    order means something.
    """
    if not members:
        return ()
    return tuple(sorted({str(member) for member in members}))


def member_digest(members: Sequence[str]) -> str:
    """A short stable digest of the canonical population, served as evidence."""
    payload = json.dumps(sorted(set(members)), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


# =========================================================================
# THE SHAPES
# =========================================================================


@dataclass(frozen=True)
class Role:
    """What the verified role may see of a book."""

    role: str
    principal_id: str
    extra_members: tuple[str, ...]
    facility_covered_only: bool


@dataclass(frozen=True)
class Record:
    entity_class: str
    edge_type: str
    entity_uri: str
    attributes: Mapping[str, str]
    dated: date | None


@dataclass(frozen=True)
class Estate:
    banker_id: str
    role: Role | None
    book: Mapping[str, str] | None
    members: tuple[str, ...]
    members_requested: tuple[str, ...]
    records: tuple[Record, ...]
    ledger_t: str
    severity_floor: Decimal
    records_materialized: int = 0
    findings: tuple[Mapping[str, str], ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return self.book is None


# =========================================================================
# THE READERS
# =========================================================================


class _Relational:
    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with psycopg.connect(self._dsn, autocommit=True) as connection, \
                connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            return [dict(row) for row in cursor.fetchall()]


class _Graph:
    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def watermark(self) -> str:
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


def role_for(role: str) -> Role:
    declared = perspectives()["perspectives"].get(role)
    if declared is None:
        raise UnknownRole(
            f"role `{role}` is not declared in `artifacts/perspectives.yaml`;"
            f" the declared roles are {sorted(perspectives()['perspectives'])}"
        )
    return Role(
        role=role,
        principal_id=str(declared["principal_id"]),
        extra_members=tuple(declared.get("members", ()) or ()),
        facility_covered_only=bool(declared.get("facility_covered_only", False)),
    )


# =========================================================================
# ACQUIRE
# =========================================================================


PRICED_INTENTS = ("portfolio-review", "credit-review", "concentration-review")


def acquire(
    *,
    banker_id: str,
    as_of: datetime,
    intent: str,
    perspective: str,
    members: Sequence[str],
    requested_classes: Sequence[str],
    requested_floor: Decimal | None,
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
) -> Estate:
    """One book, at one instant, as one role."""
    terms = vocabulary()
    tables = terms["relational"]["tables"]
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])
    watermark = graph.watermark()

    if intent not in PRICED_INTENTS:
        raise UnpricedIntent(
            f"this product prices no envelope for intent `{intent}`;"
            f" the priced intents are {list(PRICED_INTENTS)}"
        )
    role = role_for(perspective)

    declared_floor = Decimal(str(tiers()["severity_floor"]))
    floor = declared_floor if requested_floor is None else requested_floor
    if floor < declared_floor:
        raise FloorLowered(
            f"severity floor {floor} is below the declared floor {declared_floor};"
            f" a floor may be raised and never lowered"
        )

    # 1. THE BOOK. No rows -> an EMPTY estate, never a raise.
    book_rows = relational.rows(
        f"select b.banker_id, b.full_name, b.role, b.desk, count(c.lei) members"  # noqa: S608
        f" from {tables['banker']} b left join {tables['book']} c on c.banker_id = b.banker_id"
        f" where b.banker_id = %s group by 1,2,3,4",
        (banker_id,),
    )
    if not book_rows or not int(book_rows[0]["members"] or 0):
        return Estate(banker_id=banker_id, role=role, book=None, members=(),
                      members_requested=tuple(members), records=(), ledger_t=watermark,
                      severity_floor=floor)
    banker = book_rows[0]

    # 2. THE POPULATION, canonical. `members` NARROWS and never widens.
    roster = relational.rows(
        f"select c.lei, c.is_primary, c.assigned_date, e.legal_name, e.sic, e.sic_description"  # noqa: S608
        f" from {tables['book']} c left join {tables['entity']} e on e.lei = c.lei"
        f" where c.banker_id = %s order by c.lei",
        (banker_id,),
    )
    in_book = {str(row["lei"]) for row in roster}
    requested = canonical_members(members)
    unknown = [member for member in requested if member not in in_book]
    if unknown:
        raise NotInBook(
            f"{len(unknown)} requested member(s) are not in book `{banker_id}`: {unknown[:3]}"
        )
    population = requested or tuple(sorted(in_book))

    # 3. THE LIMBS, batched over the population rather than looped per member.
    facilities = relational.rows(
        f"select f.facility_id, f.borrower_lei lei, f.facility_type, f.commitment_amount,"  # noqa: S608
        f" f.maturity_date, coalesce(d.drawn, 0) drawn_amount, coalesce(d.n, 0) drawdown_count"
        f" from {tables['facility']} f"
        f" left join (select facility_id, sum(amount) drawn, count(*) n"
        f"            from {tables['drawdown']} where drawdown_date <= %s group by 1) d"
        f"   on d.facility_id = f.facility_id"
        f" where f.borrower_lei = any(%s) order by f.facility_id",
        (as_of.date(), list(population)),
    )
    covered = {str(row["lei"]) for row in facilities}
    # THE DENOMINATOR FOR COMPLETENESS is the population the CALLER asked
    # about, before the ROLE narrowed it. A caller that narrows its own
    # question is not being denied anything; a role that cannot see part of
    # the book is, and only that exclusion is the entitlement's cost
    # (`PEW-G13`, `CP-SPEC-023` §E.2).
    in_scope = len(population)
    if role.facility_covered_only:
        # FORMATIVE: a member this role may not see is never selected.
        population = tuple(member for member in population if member in covered)
        facilities = [row for row in facilities if str(row["lei"]) in set(population)]

    wanted = set(requested_classes) or set(signal_classes())
    signals = relational.rows(
        f"select signal_id, lei, signal_type, severity, observed_at, source_ref"  # noqa: S608
        f" from {tables['signal']} where lei = any(%s) and signal_type = any(%s)"
        f"   and observed_at <= %s and severity >= %s order by observed_at desc, signal_id",
        (list(population), sorted(wanted), as_of, floor),
    )
    covenants = relational.rows(
        f"select b.facility_id, f.borrower_lei lei, b.covenant_type, b.breach_date,"  # noqa: S608
        f" b.observed_value, b.threshold_at_breach, b.cured_date, b.compliant_today"
        f" from {tables['covenant']} b join {tables['facility']} f using(facility_id)"
        f" where f.borrower_lei = any(%s) and b.breach_date <= %s order by b.breach_date",
        (list(population), as_of.date()),
    )

    records = [
        *_members(roster, population=population, terms=terms),
        *_facilities(facilities, terms=terms),
        *_covenants(covenants, terms=terms),
        *_signals(signals, terms=terms),
    ]
    findings: list[Mapping[str, str]] = []
    if not covenants:
        findings.append({
            "finding": "no-covenant-history",
            "detail": "no facility in this population has a recorded covenant breach at this instant",
        })

    book = {
        "banker_id": str(banker["banker_id"]),
        "banker_name": str(banker["full_name"]),
        "banker_role": str(banker["role"]),
        "banker_desk": str(banker["desk"]),
        "member_count": str(len(population)),
        # THE FULL ROSTER, so a role that saw fewer members is not thereby
        # more complete (`PEW-G13`). The count is the book's, not the view's.
        "book_member_total": str(in_scope),
        "book_roster_total": str(len(in_book)),
        "members_requested": str(len(requested)),
        "member_digest": member_digest(population),
        "facility_covered_count": str(len({m for m in population if m in covered})),
        "severity_floor": str(floor),
        "tier_policy_version": str(yaml.safe_load(TIERS.read_text(encoding="utf-8"))["semver"]),
        "concentration_threshold_pct": str(tiers()["concentration"]["single_name_threshold_pct"]),
    }
    return Estate(
        banker_id=banker_id, role=role, book=book, members=tuple(population),
        members_requested=requested, records=tuple(records), ledger_t=watermark,
        severity_floor=floor, records_materialized=len(records), findings=tuple(findings),
    )


# =========================================================================
# RECORD BUILDERS
# =========================================================================


def _members(
    roster: Sequence[Mapping[str, Any]], *, population: Sequence[str], terms: Mapping[str, Any]
) -> list[Record]:
    keep = set(population)
    return [
        Record(entity_class="member", edge_type="hasMember",
               entity_uri=f"{terms['entity_uri_prefix']['member']}{row['lei']}",
               attributes={
                   "lei": str(row["lei"]),
                   "legal_name": str(row["legal_name"] or ""),
                   "sic": str(row["sic"] or ""),
                   "sic_description": str(row["sic_description"] or ""),
                   # MEMBERSHIP AS AN ENTITY ATTRIBUTE, not an edge — so
                   # per-member supersession reaches the invalidation register
                   # (`CP-SPEC-023` §C.3 trap 1, Gate 0's Q16).
                   "in_book": "true",
                   "is_primary": str(bool(row["is_primary"])).lower(),
                   "assigned_date": str(row["assigned_date"]),
                   "classification": terms["classification"]["assignment"]["member"],
               }, dated=None)
        for row in roster if str(row["lei"]) in keep
    ]


def _facilities(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="facility", edge_type="hasFacility",
               entity_uri=f"{terms['entity_uri_prefix']['facility']}{row['facility_id']}",
               attributes={
                   "facility_id": str(row["facility_id"]),
                   "lei": str(row["lei"]),
                   "facility_type": str(row["facility_type"] or ""),
                   "commitment_amount": str(row["commitment_amount"]),
                   "drawn_amount": str(row["drawn_amount"]),
                   # THE COUNT, so zero-because-undrawn and zero-because-
                   # unobserved are distinguishable (`PEW-G15`).
                   "drawdown_count": str(row["drawdown_count"]),
                   "maturity_date": str(row["maturity_date"] or ""),
                   "classification": terms["classification"]["assignment"]["facility"],
               }, dated=None)
        for row in rows
    ]


def _covenants(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="covenant", edge_type="hasCovenant",
               entity_uri=f"{terms['entity_uri_prefix']['covenant']}{row['facility_id']}:{row['breach_date']}",
               attributes={
                   "facility_id": str(row["facility_id"]),
                   "lei": str(row["lei"]),
                   "covenant_type": str(row["covenant_type"]),
                   "breach_date": str(row["breach_date"]),
                   "observed_value": str(row["observed_value"]),
                   "threshold_at_breach": str(row["threshold_at_breach"]),
                   "cured_date": str(row["cured_date"] or ""),
                   "compliant_today": str(bool(row["compliant_today"])).lower(),
                   "classification": terms["classification"]["assignment"]["covenant"],
               }, dated=_as_date(row["breach_date"]))
        for row in rows
    ]


def _signals(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    """One record per signal, in the ENTITY CLASS its own `λ_c` governs."""
    classes = signal_classes()
    edges = terms["signal_edges"]
    out: list[Record] = []
    for row in rows:
        entity_class = classes.get(str(row["signal_type"]))
        if entity_class is None:
            continue
        out.append(Record(
            entity_class=entity_class, edge_type=edges[entity_class],
            entity_uri=f"{terms['entity_uri_prefix']['signal']}{row['signal_id']}",
            attributes={
                "signal_id": str(row["signal_id"]),
                "lei": str(row["lei"]),
                "signal_type": str(row["signal_type"]),
                "severity": str(row["severity"]),
                "observed_at": str(row["observed_at"]),
                "source_ref": str(row["source_ref"] or ""),
                "classification": terms["classification"]["assignment"]["signal"],
            },
            dated=_as_date(row["observed_at"]),
        ))
    return out


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
