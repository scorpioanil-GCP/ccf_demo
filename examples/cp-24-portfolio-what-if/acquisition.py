"""The estate half of `cib.portfolio-what-if` — one book, many members.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's.

THE ASSEMBLY UNIT IS A POPULATION (`CP-SPEC-024` §0.2a). Every earlier rung
anchored on one thing; here the members *are* the answer, and the reads are
batched per limb over the whole population rather than looped per member.

THE ORDER IS THE POINT. The caller's role is resolved FIRST, because it decides
which members and which measures may be assembled at all — a member a role may
not see is never selected, not filtered afterwards.

NOTHING HERE READS THE SCENARIO, AND THAT IS THE GOVERNING RULE
(`CP-SPEC-024` §D.3, ruled 2026-09-21). This module acquires only OBSERVED
evidence. The assumptions reach Pi as the effective request and never become a
claim, so no scenario magnitude can end up carrying source lineage
(`WIF-G06`). What this module does carry into every claim is the observation's
own instant and age — a scenario does not refresh its factual inputs, and a
stressed stale valuation is still stale (`WIF-G11`).

SECOND INSTANCE OF THIS POPULATION READER (`WIF-F-01`, ruled a friction
MEASUREMENT only). The book, member and facility readers below are rung 23's,
adapted. No abstraction is pre-authorized; if a third rung writes the same
reader, all three are measured before anything is proposed.

MEMBERSHIP IS A STANDING STATE, NOT A DATED EVENT (`D-IMPL-332`). A book is *as
it stands*: `coverage_assignment` carries an `assigned_date` and no end date, so
this product does not claim to reconstruct a historical book. The collateral
valuations and the base rate are dated events and carry their day.
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
SENSITIVITIES = HERE / "artifacts" / "sensitivities.yaml"


class NotInBook(ValueError):
    """The caller named a member that is not in this book."""


class UnpricedIntent(ValueError):
    """The caller named an intent this product prices no envelope for."""


class FloorLowered(ValueError):
    """The caller asked for a coverage floor below the declared one."""


class ScenarioOutOfBounds(ValueError):
    """A scenario magnitude falls outside the declared bounds."""


class NoncanonicalMagnitude(ValueError):
    """A scenario magnitude was not an integer in canonical units."""


class UnknownRole(ValueError):
    """The caller's role is not declared in `artifacts/perspectives.yaml`."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def perspectives() -> Mapping[str, Any]:
    return yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def sensitivities() -> Mapping[str, Any]:
    return yaml.safe_load(SENSITIVITIES.read_text(encoding="utf-8"))["declaration"]


def basis_point() -> Decimal:
    """The exact fraction a basis point is — used INSIDE the arithmetic only.

    `Q1`, ruled 2026-09-21: the wire carries the integer; this `Decimal` never
    crosses a boundary.
    """
    return Decimal(str(sensitivities()["basis_point"]))


def required_classes() -> tuple[str, ...]:
    """The classes a complete book would carry."""
    return ("book", "member", "facility", "collateral", "rate")


@dataclass(frozen=True)
class Scenario:
    """The bound assumptions — INTEGERS IN CANONICAL UNITS, never fractions.

    This is not evidence. It reaches Pi through the effective request and is
    never minted as a claim (`CP-SPEC-024` §D.3).
    """

    rate_shift_bp: int
    collateral_shift_bp: int
    collateral_class: str
    horizon_months: int

    def as_attributes(self) -> Mapping[str, str]:
        return {
            "rate_shift_bp": str(self.rate_shift_bp),
            "collateral_shift_bp": str(self.collateral_shift_bp),
            "collateral_class": self.collateral_class,
            "horizon_months": str(self.horizon_months),
        }


def refuse_noncanonical(raw: Mapping[str, Any]) -> None:
    """Refuse a noncanonical magnitude BEFORE a request is built — never coerce.

    `Q1`, ruled 2026-09-21. A float is not rounded, not truncated and not
    converted: it is refused, with the canonical unit named so the caller can
    fix the call. 150 basis points is `150`, never `0.015`.
    """
    for name in ("rate_shift_bp", "collateral_shift_bp", "horizon_months"):
        given = raw.get(name)
        if given is None:
            continue
        if isinstance(given, bool) or not isinstance(given, int):
            raise NoncanonicalMagnitude(
                f"`scenario.{name}` must be an INTEGER in canonical units (basis points);"
                f" got {given!r} of type {type(given).__name__}. It is refused rather than"
                f" coerced — 150 basis points is `150`, not `0.015`, and rounding here would"
                f" produce a content address nobody could reproduce"
            )


def bind_scenario(raw: Mapping[str, Any]) -> Scenario:
    """Validate the closed object, in canonical units, refusing rather than coercing.

    `WIF-G02` — an undeclared member is refused. `WIF-G03` — a magnitude
    outside the declared bounds is refused by name. `WIF-G04` — a
    noncanonical fractional form is **refused, never coerced or rounded**.
    """
    declared = ("rate_shift_bp", "collateral_shift_bp", "collateral_class", "horizon_months")
    unknown = sorted(set(raw) - set(declared))
    if unknown:
        raise ScenarioOutOfBounds(f"the scenario names undeclared member(s) {unknown}")
    if "rate_shift_bp" not in raw:
        raise ScenarioOutOfBounds("the scenario states no `rate_shift_bp`, which is required")

    bounds = sensitivities()["bounds"]
    values: dict[str, Any] = {}
    for name in ("rate_shift_bp", "collateral_shift_bp", "horizon_months"):
        given = raw.get(name)
        if given is None:
            values[name] = 0 if name != "horizon_months" else int(
                sensitivities()["rate"]["default_horizon_months"])
            continue
        # A FLOAT IS REFUSED, NOT ROUNDED. `bool` is an `int` subclass and is
        # not a magnitude, so it is refused too.
        if isinstance(given, bool) or not isinstance(given, int):
            raise NoncanonicalMagnitude(
                f"`{name}` must be an INTEGER in canonical units (basis points);"
                f" got {given!r} of type {type(given).__name__}. A fractional form is"
                f" refused rather than coerced: 150 basis points is `150`, not `0.015`"
            )
        limit = bounds.get(name)
        if limit is not None and not (int(limit["minimum"]) <= given <= int(limit["maximum"])):
            raise ScenarioOutOfBounds(
                f"`{name}` is {given}, outside the declared domain"
                f" [{limit['minimum']}, {limit['maximum']}]"
            )
        values[name] = given
    category = str(raw.get("collateral_class", "") or "")
    return Scenario(
        rate_shift_bp=int(values["rate_shift_bp"]),
        collateral_shift_bp=int(values["collateral_shift_bp"]),
        collateral_class=category,
        horizon_months=int(values["horizon_months"]),
    )


# =========================================================================
# THE MEMBER SET — canonicalized by the DEPLOYMENT, because it is a SET
# =========================================================================


def canonical_members(members: Sequence[str] | None) -> tuple[str, ...]:
    """Deduplicate and sort — the deployment's canonicalization (`Q2`, ruled).

    CP-23 knows its portfolio membership is **semantically a set**, so the
    deployment owns this rather than the SDK: a `ProductRequest` carrying
    `["A","B","C"]` and one carrying `["C","B","A"]` canonicalize to the same
    tuple, so they build the SAME effective request and hash to the same
    content address (`WIF-G05`). A genuinely different membership still
    produces a different one (`WIF-G06`).

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
    coverage_floor: Decimal
    scenario: Scenario | None = None
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


PRICED_INTENTS = ("stress-test", "credit-review", "what-if")


def acquire(
    *,
    banker_id: str,
    as_of: datetime,
    intent: str,
    perspective: str,
    members: Sequence[str],
    scenario: Scenario,
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

    declared_floor = Decimal(str(sensitivities()["coverage"]["default_floor_bp"]))
    floor = declared_floor if requested_floor is None else requested_floor
    if floor < declared_floor:
        raise FloorLowered(
            f"coverage floor {floor} is below the declared floor {declared_floor};"
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
                      coverage_floor=floor, scenario=scenario)
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
    # (`WIF-G13`, `CP-SPEC-024` §E.2).
    in_scope = len(population)
    if role.facility_covered_only:
        # FORMATIVE: a member this role may not see is never selected.
        population = tuple(member for member in population if member in covered)
        facilities = [row for row in facilities if str(row["lei"]) in set(population)]

    # COLLATERAL — the observed valuations the scenario will stress. Their
    # `valuation_date` and age come with them and are never reset (`WIF-G11`).
    collateral = relational.rows(
        f"select asset_id, pledgor_lei lei, category, valuation, valuation_date,"  # noqa: S608
        f" valuation_age_days, haircut from {tables['collateral']}"
        f" where pledgor_lei = any(%s) and valuation_date <= %s order by asset_id",
        (list(population), as_of.date()),
    )

    # THE OBSERVED BASE RATE at the decision instant — a claim with source
    # lineage. The SHIFT is not acquired: it is an assumption (`WIF-G06`).
    series = str(sensitivities().get("base_rate_series", "SOFR"))
    rates = relational.rows(
        f"select series_id, obs_date, value_pct, unit, label from {tables['rate']}"  # noqa: S608
        f" where series_id = %s and obs_date <= %s order by obs_date desc limit 1",
        (series, as_of.date()),
    )

    records = [
        *_members(roster, population=population, terms=terms),
        *_facilities(facilities, terms=terms),
        *_collateral(collateral, terms=terms),
        *_rates(rates, terms=terms),
    ]
    findings: list[Mapping[str, str]] = []
    if not rates:
        findings.append({
            "finding": "no-observed-base-rate",
            "detail": f"no `{series}` observation at or before this instant; the rate limb is unavailable",
        })
    if not collateral:
        findings.append({
            "finding": "no-observed-collateral",
            "detail": "no member of this population has a collateral valuation at this instant",
        })

    book = {
        "banker_id": str(banker["banker_id"]),
        "banker_name": str(banker["full_name"]),
        "banker_role": str(banker["role"]),
        "banker_desk": str(banker["desk"]),
        "member_count": str(len(population)),
        # THE FULL ROSTER, so a role that saw fewer members is not thereby
        # more complete (`WIF-G13`). The count is the book's, not the view's.
        "book_member_total": str(in_scope),
        "book_roster_total": str(len(in_book)),
        "members_requested": str(len(requested)),
        "member_digest": member_digest(population),
        "facility_covered_count": str(len({m for m in population if m in covered})),
        "coverage_floor_bp": str(floor),
        "sensitivity_version": str(
            yaml.safe_load(SENSITIVITIES.read_text(encoding="utf-8"))["semver"]),
        # THE ASSUMPTIONS ARE ECHOED ON THE BOOK CLAIM so a reader can see what
        # conditioned the answer — but they are NOT evidence, and `WIF-G06`
        # proves no OTHER claim carries them. The authoritative record of the
        # assumptions is the effective request, not this echo.
        **scenario.as_attributes(),
        "base_rate_series": str(rates[0]["series_id"]) if rates else "",
        "base_rate_pct": str(rates[0]["value_pct"]) if rates else "",
        "base_rate_observed_at": str(rates[0]["obs_date"]) if rates else "",
    }
    return Estate(
        banker_id=banker_id, role=role, book=book, members=tuple(population),
        members_requested=requested, records=tuple(records), ledger_t=watermark,
        coverage_floor=floor, scenario=scenario,
        records_materialized=len(records), findings=tuple(findings),
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
                   # (`CP-SPEC-024` §C.3 trap 1, Gate 0's Q16).
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
                   # unobserved are distinguishable (`WIF-G15`).
                   "drawdown_count": str(row["drawdown_count"]),
                   "maturity_date": str(row["maturity_date"] or ""),
                   "classification": terms["classification"]["assignment"]["facility"],
               }, dated=None)
        for row in rows
    ]


def _collateral(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    """The OBSERVED valuations, each carrying its own instant and age.

    The age is minted onto the claim rather than recomputed later, so a
    stressed figure can state the staleness of the observation it came from
    without any chance of a second clock drifting (`WIF-G11`).
    """
    return [
        Record(entity_class="collateral", edge_type="hasCollateral",
               entity_uri=f"{terms['entity_uri_prefix']['collateral']}{row['asset_id']}",
               attributes={
                   "asset_id": str(row["asset_id"]),
                   "lei": str(row["lei"]),
                   "category": str(row["category"]),
                   "valuation": str(row["valuation"]),
                   "valuation_date": str(row["valuation_date"]),
                   "valuation_age_days": str(row["valuation_age_days"]),
                   # THE ESTATE'S OWN HAIRCUT. A scenario never alters it.
                   "haircut": str(row["haircut"]),
                   "classification": terms["classification"]["assignment"]["collateral"],
               }, dated=_as_date(row["valuation_date"]))
        for row in rows
    ]


def _rates(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    """The observed base rate — a fact with source lineage, not an assumption."""
    return [
        Record(entity_class="rate", edge_type="hasRate",
               entity_uri=f"{terms['entity_uri_prefix']['rate']}{row['series_id']}:{row['obs_date']}",
               attributes={
                   "series_id": str(row["series_id"]),
                   "obs_date": str(row["obs_date"]),
                   "value_pct": str(row["value_pct"]),
                   "unit": str(row["unit"] or ""),
                   "label": str(row["label"] or ""),
                   "classification": terms["classification"]["assignment"]["rate"],
               }, dated=_as_date(row["obs_date"]))
        for row in rows
    ]


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
