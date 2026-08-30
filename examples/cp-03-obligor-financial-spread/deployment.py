"""What this deployment KNOWS: its estate, its vocabulary, and this question's values.

[ADAPT] all of it. [MECHANISM] nothing — every CCF call is in `produce.py`.

**THE SEAM.** `produce.py` is the fabric's call spine and names no table, no
column and no domain word. This module names all of them and makes no fabric
call. `read()` is the one function the spine invokes, and it hands back a
`SpreadScenario` carrying this question's answers.

**WHAT THIS PRODUCT IS.** One obligor's standardized financial spread, where
every figure names the period it describes, the filing that asserted it, and
whether a later filing changed it. Spec §A: temporal validity is an
ATTRIBUTE-level property — a product does not have *a* freshness, each of its
claims does.

**ONE STORE.** PostgreSQL `ccf_v2`, and nothing else is opened. A Fluree
policy-version binding was specified for this product and then removed from it
(Dave, 2026-08-30); `policy_version` comes from the Control Plane artifact in
force. `OFS-G05` asserts no other store is reached.

**THE THREE READS THAT ARE NOT ONE READ.** Resolution goes through rung 01's
crosswalk (`OFS-G02`); the facts are ONE batched select for all periods and all
tags (§7.4 N+1 avoidance, never one query per period); peers are a separate
conditional read joined on `period_end` and NEVER on filing date, because
comparing a Q3 figure to a peer's Q2 because they filed the same week is the
classic spreading error and the join key forecloses it.
"""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg
import yaml

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.artifacts import (
    DebtProfile,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.deployment import BootedFabric
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"

CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
RESTATEMENT = ARTIFACTS / "restatement.yaml"
SPREAD_LINES = ARTIFACTS / "spread-lines.yaml"
SPEC = HERE / "spec" / "CP-SPEC-003_Obligor_Financial_Spread.md"

DECLARATION = "declaration"
PROFILES = "profiles"
SOURCES = "sources"
SETTINGS = "settings"
FROM_ENV = "from_env"
REMEDY = "remedy"

KEY_PERSPECTIVE = "default_perspective"
KEY_PRODUCT_CLASS = "product_class"
KEY_POLICY_OPERATOR = "policy.principal-subgraph"
KEY_REQUEST_CONTRACT = "request_contract"
KEY_RESOLUTION = "resolution"
KEY_HALF_LIFE_TABLE = "half_life"
KEY_DEBT_PROFILE = "debt_profile"
KEY_POLICY_BUNDLE = "policy"

REPLAY_RECORD_CLASS = "cp-03.replay-record"
QUERY_PIN_CLASS = "cp-03.graph-query"
ARTIFACT_STORE_DIRNAME = "artifacts-store"

#: Served where a claim cannot be evaluated. NEVER `0` — a zero revenue reads as
#: a company with no sales, which is a different and false statement.
NOT_EVALUABLE = "NOT_EVALUABLE"

PARAM_INTENT = "intent"
PARAM_PERIODS = "periods"
PARAM_BASIS = "basis"
PARAM_INCLUDE_PEERS = "include_peers"
PARAM_PEER_BASIS = "peer_basis"
PARAM_DEBT_TOLERANCE = "debt_tolerance"
PARAM_AS_OF = "as_of"

BASIS_AS_REPORTED = "as-reported"
BASIS_LATEST_RESTATED = "latest-restated"

SOURCE_BINDING = "financial_spread"
SOURCE_SETTING_DSN = "dsn"

SOURCE_SCHEMA = "ccf_v2"
TABLE_FACT = "financial_fact"
TABLE_PEER_FACT = "peer_fact"
TABLE_PEER_ENTITY = "peer_entity"
TABLE_ENTITY = "legal_entity"
TABLE_CROSSWALK = "crosswalk"
TABLE_FILING_PROFILE = "filing_profile"
TABLE_PRINCIPAL = "principal"
TABLE_PRINCIPAL_JURISDICTION = "principal_jurisdiction"

SIGNAL_ANNUAL = "annual_facts"
SIGNAL_QUARTERLY = "quarterly_facts"
SIGNAL_RESTATEMENT = "restatement"
SIGNAL_PEER = "peer_set"

ATTR_MATCH_KEY = "obligor_ref"
ATTR_LEI = "lei"
ATTR_CIK = "cik"
ATTR_NAME = "obligor_legal_name"
ATTR_JURISDICTION = "obligor_jurisdiction"
ATTR_FY_END_MONTH = "fiscal_year_end_month"
ATTR_LATEST_FILED = "latest_filed_date"
ATTR_FORMALLY_RESTATED = "formally_restated"
ATTR_PERIODS = "spread_periods"
ATTR_PEERS = "peer_comparison"

CLASS_PRECISION = "precision"
CLASS_MATERIAL = "material"


# ---------------------------------------------------------------------------
# Reading the deployment's own documents.
# ---------------------------------------------------------------------------


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def config() -> Mapping[str, Any]:
    return _load(CONFIG)


def question() -> Mapping[str, Any]:
    return _load(QUESTION)[DECLARATION]


def ttl_declaration() -> Mapping[str, Any]:
    return _load(TTL)[DECLARATION]


def restatement_rule() -> Mapping[str, Any]:
    """The key and the threshold — §C.4 trap 1 and §E.5, never code constants."""
    return _load(RESTATEMENT)[DECLARATION]


def spreading_convention() -> Mapping[str, Any]:
    """Tag map, ratio definitions and adjustments — §C.1 elements 6, 7 and 8."""
    return _load(SPREAD_LINES)[DECLARATION]


def source_dsn() -> str:
    """The read-only DSN, from the environment named by `backends.yaml`.

    No default and no in-tree fallback: an unset variable raises carrying the
    remedy the document declares, because a deployment that quietly reached a
    different store than the one it names is the failure this refuses.
    """
    binding = _load(BACKENDS)[DECLARATION][SOURCES][SOURCE_BINDING][SETTINGS]
    setting = binding[SOURCE_SETTING_DSN]
    variable = setting[FROM_ENV]
    dsn = os.environ.get(variable)
    if not dsn:
        raise SystemExit(f"{variable} is not set.\n\n{setting[REMEDY]}")
    return dsn


# ---------------------------------------------------------------------------
# Value helpers. Each one exists because the source and the contract disagree
# about a representation, and the disagreement is resolved HERE rather than in
# the spine.
# ---------------------------------------------------------------------------


def _instant(value: date) -> datetime:
    """A source DATE as a UTC instant at midnight.

    Widening a date to an instant is a lossless statement about when the fact is
    known to have held BY. Narrowing the other way would invent a time of day.
    """
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _text(value: Any) -> str | None:
    """A source value as text, or None when the source did not carry it.

    An absent key is a real completeness shortfall that `C_attributes` counts;
    a blank string measures as PRESENT and would hide the shortfall.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: Any) -> Decimal | None:
    """A source numeric as `Decimal`, never as `float`.

    A float is not bit-stable across platforms, so it cannot be canonically
    encoded and cannot appear in a content address. The fabric refuses one; this
    is where the refusal is avoided rather than met.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _relative_change(first: Decimal | None, last: Decimal | None) -> Decimal | None:
    """|last - first| / |first|, or None where the ratio is undefined.

    `first` of zero or absent yields no defined relative change. The class is
    then `NOT_EVALUABLE` — never a division, and never a silent default to
    `material`, which would inflate the material population with arithmetic
    accidents.
    """
    if first is None or last is None or first == 0:
        return None
    return abs((last - first) / abs(first))


# ---------------------------------------------------------------------------
# What one read of the system of record produced.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedObligor:
    """The anchor, resolved — identity and the context the policy step needs."""

    lei: str
    cik: int
    legal_name: str | None
    jurisdiction: str
    internal_client_id: str | None
    fiscal_year_end_month: int | None
    latest_filed: date | None
    #: SEC 8-K Item 4.02, "Non-Reliance on Previously Issued Financial
    #: Statements" — the filer's own declaration. CORROBORATION ONLY: it covers
    #: 9 of the 37 obligors whose values actually change (§C.4 trap 2), so a
    #: build that detected restatement from it would miss 28.
    has_non_reliance_filing: bool


@dataclass(frozen=True)
class FactCell:
    """One fact-cell: the same fact as the estate's own key defines it.

    The identity key is `(lei, tag, unit, period_end, fiscal_period)` — the
    store's `PRIMARY KEY` minus `accession`, which is exactly what a restatement
    varies. §C.4 trap 1: shorter keys invent restatements out of currency and
    duration artifacts.
    """

    tag: str
    unit: str
    period_start: date | None
    period_end: date
    fiscal_period: str
    #: The value under the requested `basis`, and the accession that asserted it.
    value: Decimal | None
    accession: str
    filed_date: date
    form: str
    #: True when a later filing carried a DIFFERENT value for this cell.
    restated: bool
    #: `precision` | `material` | NOT_EVALUABLE — read from the artifact's
    #: threshold, never from a constant. `OFS-G13` asserts the artifact is read.
    restatement_class: str | None

    @property
    def is_instant(self) -> bool:
        """Balance-sheet facts carry no `period_start`. 8,088 of 15,055."""
        return self.period_start is None


@dataclass(frozen=True)
class SourceRead:
    """Everything one question needed from the store, read and shaped."""

    resolved: ResolvedObligor | None
    cells: tuple[FactCell, ...]
    peers: tuple[Mapping[str, Any], ...]
    permitted_jurisdictions: tuple[str, ...]


# ---------------------------------------------------------------------------
# The reads. Three, and they are deliberately not one.
# ---------------------------------------------------------------------------


def _resolve_obligor(cur: Any, anchor: str) -> ResolvedObligor | None:
    """Resolve the anchor THROUGH rung 01's crosswalk — `OFS-G02`.

    `financial_fact` carries both `lei` and `cik`, so this product COULD resolve
    without the crosswalk. It must not. The `cik` on the fact table is a
    denormalized convenience of this estate; the authority for LEI→CIK is rung
    01's crosswalk, and a product that read the local column would silently stop
    depending on its declared prerequisite — and keep working right up until an
    estate without that column.

    The `filing_profile` join is LEFT: 39 of 50 obligors have no Item 4.02 row,
    and their absence is a fact rather than a reason to fail resolution.
    """
    cur.execute(
        f"""
        select xw.lei, xw.cik, xw.internal_client_id,
               le.legal_name, le.legal_jurisdiction,
               coalesce(fp.count_8k_item_4_02, 0) as non_reliance_filings,
               (select max(f.filed_date)
                  from {SOURCE_SCHEMA}.{TABLE_FACT} f
                 where f.lei = xw.lei) as latest_filed,
               (select extract(month from max(f.period_end))
                  from {SOURCE_SCHEMA}.{TABLE_FACT} f
                 where f.lei = xw.lei
                   and f.fiscal_period = 'FY' and f.form = '10-K') as fy_end_month
          from {SOURCE_SCHEMA}.{TABLE_CROSSWALK} xw
          join {SOURCE_SCHEMA}.{TABLE_ENTITY} le on le.lei = xw.lei
     left join {SOURCE_SCHEMA}.{TABLE_FILING_PROFILE} fp on fp.lei = xw.lei
         where xw.lei = %s
        """,
        (anchor,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    lei, cik, client_id, name, jurisdiction, filings, latest, fy_month = row
    if jurisdiction is None:
        # The policy step filters on this attribute. An obligor arriving without
        # it would be admitted or refused on a MISSING VALUE rather than on a
        # grant, which is a different decision wearing the same outcome.
        return None
    return ResolvedObligor(
        lei=str(lei).strip(),
        cik=int(cik),
        legal_name=_text(name),
        jurisdiction=str(jurisdiction).strip(),
        internal_client_id=_text(client_id),
        fiscal_year_end_month=int(fy_month) if fy_month is not None else None,
        latest_filed=latest,
        has_non_reliance_filing=int(filings) > 0,
    )


def _read_cells(
    cur: Any, anchor: str, *, periods: int, basis: str, threshold: Decimal
) -> tuple[FactCell, ...]:
    """ONE query for all periods and all tags — §7.4 N+1 avoidance.

    Not one query per period, and not one per tag. The article is explicit that
    batching is mandatory rather than a variant, and a product above T2 meets its
    contract and misses its SLO without it.

    **THE BASIS SELECTS WITHIN A CELL, NOT ACROSS CELLS.** `as-reported` takes
    the EARLIEST accession for each fact-cell; `latest-restated` takes the
    latest. Both return one row per cell — the parameter changes WHICH filing
    speaks for the cell, never how many cells there are.

    **The restatement flag and its class are computed in the same pass**, from
    the first- and last-filed values of the cell, so no second query and no
    second definition of "restated" can drift from this one.
    """
    order = "asc" if basis == BASIS_AS_REPORTED else "desc"
    cur.execute(
        f"""
        with ranked as (
            select f.tag, f.unit, f.period_start, f.period_end, f.fiscal_period,
                   f.value, f.accession, f.filed_date, f.form,
                   -- `count(distinct ...) over w` is not implemented in
                   -- Postgres. `min <> max` is the exact equivalent for
                   -- "more than one distinct value", and it is NOT the same as
                   -- `first_value <> last_value`: a cell filed 100, then 200,
                   -- then 100 again has two distinct values and identical
                   -- endpoints, and comparing endpoints would call it unchanged.
                   min(f.value) over w                              as min_value,
                   max(f.value) over w                              as max_value,
                   first_value(f.value)      over (partition by f.tag, f.unit,
                                                                f.period_start,
                                                                f.period_end,
                                                                f.fiscal_period
                                                   order by f.filed_date asc)  as first_value,
                   first_value(f.value)      over (partition by f.tag, f.unit,
                                                                f.period_start,
                                                                f.period_end,
                                                                f.fiscal_period
                                                   order by f.filed_date desc) as last_value,
                   row_number()              over (partition by f.tag, f.unit,
                                                                f.period_start,
                                                                f.period_end,
                                                                f.fiscal_period
                                                   order by f.filed_date {order},
                                                            f.accession {order}) as pick
              from {SOURCE_SCHEMA}.{TABLE_FACT} f
             where f.lei = %s
            window w as (partition by f.tag, f.unit, f.period_start,
                                      f.period_end, f.fiscal_period)
        ),
        recent as (
            select distinct period_end from ranked order by period_end desc limit %s
        )
        select r.tag, r.unit, r.period_start, r.period_end, r.fiscal_period,
               r.value, r.accession, r.filed_date, r.form,
               (r.min_value is distinct from r.max_value) as restated,
               r.first_value, r.last_value
          from ranked r
          join recent on recent.period_end = r.period_end
         where r.pick = 1
         order by r.period_end desc, r.tag
        """,
        (anchor, periods),
    )

    cells: list[FactCell] = []
    for row in cur.fetchall():
        (tag, unit, p_start, p_end, fiscal, value,
         accession, filed, form, restated, first_v, last_v) = row
        restated = bool(restated)
        klass: str | None = None
        if restated:
            change = _relative_change(_decimal(first_v), _decimal(last_v))
            if change is None:
                klass = NOT_EVALUABLE
            else:
                klass = CLASS_MATERIAL if change >= threshold else CLASS_PRECISION
        cells.append(
            FactCell(
                tag=str(tag),
                unit=str(unit),
                period_start=p_start,
                period_end=p_end,
                fiscal_period=str(fiscal),
                value=_decimal(value),
                accession=str(accession),
                filed_date=filed,
                form=str(form),
                restated=restated,
                restatement_class=klass,
            )
        )
    return tuple(cells)
