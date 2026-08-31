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

import ast
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

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
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
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

#: The `fiscal_period` value that marks a full year. Everything else is a
#: quarter, and the distinction picks the signal class a cell decays against —
#: §E.1's whole subject. A single `period_end` carries BOTH: Digital Turbine's
#: 2026-03-31 holds an `FY` cell and a `Q1` cell, which is why a spread period
#: is keyed `(period_end, fiscal_period)` and never by `period_end` alone.
FISCAL_ANNUAL = "FY"

#: The declared-fallback operator in a ratio expression: `a ?? b` takes `a`
#: where it is defined and `b` otherwise. Not Python, so the expression is split
#: on it before parsing — see `_alternatives`.
COALESCE = "??"

KEY_TAG_MAP = "tag_map"
KEY_RATIOS = "ratios"
KEY_ADJUSTMENTS = "adjustments"
KEY_TAGS = "tags"
KEY_KIND = "kind"
KEY_EXPRESSION = "expression"
KEY_INPUTS = "inputs"
KEY_UNIT = "unit"
KEY_MIXED_KIND = "mixed_kind_tags"
KIND_INSTANT = "instant"


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
    peers: tuple[PeerFact, ...]
    permitted_jurisdictions: tuple[str, ...]
    envelopes: tuple[SignalEnvelope, ...]


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


def _permitted_jurisdictions(cur: Any, *, principal_id: str) -> tuple[str, ...]:
    """The calling principal's grant set, EXPANDED against the estate.

    A principal is granted a jurisdiction PREFIX — `US` reaches `US-DE`,
    `US-MD`, `US-NV`. `src/ccf/operators/categories.py::PolicyFilter` tests
    EXACT membership of `permitted_classifications`, so a prefix handed to it
    unexpanded matches nothing and empties the view.

    The expansion is therefore the deployment's, and it is done against the
    jurisdictions the estate actually holds rather than against an invented
    list. Returning the prefix itself alongside its expansions is deliberate: an
    obligor whose jurisdiction IS the bare prefix is granted by the same row.

    **This is rung 01's pattern, re-measured rather than inherited on faith.**
    The expansion reads `legal_entity`, because §B.2 binds the classification to
    the OBLIGOR'S jurisdiction — a financial fact has no nationality of its own,
    it inherits the filer's.
    """
    cur.execute(
        f"""
        select distinct le.legal_jurisdiction
          from {SOURCE_SCHEMA}.{TABLE_ENTITY} le
          join {SOURCE_SCHEMA}.{TABLE_PRINCIPAL_JURISDICTION} pj
            on le.legal_jurisdiction = pj.jurisdiction_prefix
            or le.legal_jurisdiction like pj.jurisdiction_prefix || '-%%'
         where pj.principal_id = %s
           and le.legal_jurisdiction is not null
        """,
        (principal_id,),
    )
    return tuple(sorted(str(row[0]) for row in cur.fetchall()))


# ---------------------------------------------------------------------------
# The third read — peers. The JOIN KEY is the entire point of this function.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeerFact:
    """One peer's figure, at a `period_end` IDENTICAL to one the anchor carries.

    There is no `filed_date` in the join and that is not an omission. Matching
    peers on filing date is the classic spreading error — it compares a Q3
    figure to a peer's Q2 because the two filed the same week — and the join key
    forecloses it structurally rather than by a reviewer noticing.
    """

    cik: int
    entity_name: str | None
    sic: str | None
    tag: str
    unit: str
    period_start: date | None
    period_end: date
    fiscal_period: str
    value: Decimal | None
    filed_date: date | None


def _read_peers(
    cur: Any,
    *,
    sic: str | None,
    period_ends: Sequence[date],
    exclude_cik: int,
) -> tuple[PeerFact, ...]:
    """The peer cohort's facts at the anchor's own period ends — §D.2 step 4.

    **Degrades, never fails.** A cohort of nobody is a legitimate answer: this
    estate's `peer_entity` carries no row at all for some SIC codes, so an
    obligor can be structurally peerless. That is a completeness shortfall which
    `S` counts, and never an exception — a peer read is a comparison, and a
    product whose comparison is empty is still a correct spread.

    One query for the whole cohort and every period, on the same §7.4 N+1
    reasoning as `_read_cells`: not one query per peer, and not one per period.
    """
    if sic is None or not period_ends:
        return ()
    cur.execute(
        f"""
        select pf.cik, pe.entity_name, pe.sic, pf.tag, pf.unit,
               pf.period_start, pf.period_end, pf.fiscal_period,
               pf.value, pf.filed_date
          from {SOURCE_SCHEMA}.{TABLE_PEER_FACT} pf
          join {SOURCE_SCHEMA}.{TABLE_PEER_ENTITY} pe on pe.cik = pf.cik
         where pe.sic = %s
           and pf.cik <> %s
           and pf.period_end = any(%s)
         order by pf.period_end desc, pe.cik, pf.tag
        """,
        (sic, exclude_cik, list(period_ends)),
    )
    return tuple(
        PeerFact(
            cik=int(row[0]),
            entity_name=_text(row[1]),
            sic=_text(row[2]),
            tag=str(row[3]),
            unit=str(row[4]),
            period_start=row[5],
            period_end=row[6],
            fiscal_period=str(row[7]),
            value=_decimal(row[8]),
            filed_date=row[9],
        )
        for row in cur.fetchall()
    )


# ---------------------------------------------------------------------------
# Step 5 — derivation. In-memory, algorithmic, and NO LLM is reachable from it
# (`OFS-G07`). What follows is an INTERPRETER over the declared convention; the
# ratio definitions themselves live in `artifacts/spread-lines.yaml` because
# "a change to the leverage definition changes every derived figure, which is
# why the definition is versioned policy rather than code."
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Figure:
    """A computed amount and THE FACT-CELL LINES IT ACTUALLY CONSUMED.

    `consumed` is the load-bearing half. §D.6 requires every derived line to
    name its inputs and `OFS-G12` asserts each entry resolves to a fact-cell in
    the SAME payload — so the set is collected during evaluation from the names
    the arithmetic really read, never copied from the artifact's declared
    `inputs:` list.

    **The two differ, and that is the point.** `total_debt` declares three
    inputs and consumes either one (`total_debt_reported`) or two
    (`long_term_debt + current_debt`) depending on which branch of the `??`
    fallback was taken. Publishing the declared list would name a fact-cell the
    payload never read.
    """

    amount: Decimal | None
    consumed: frozenset[str]

    @property
    def evaluable(self) -> bool:
        return self.amount is not None


UNDEFINED = Figure(amount=None, consumed=frozenset())


def _alternatives(expression: str) -> tuple[str, ...]:
    """Split a ratio expression on its TOP-LEVEL `??` fallbacks.

    `??` is not Python, so it cannot survive into `ast.parse`. Splitting first
    leaves each alternative a plain arithmetic expression, and the fallback
    becomes control flow — evaluate left to right, take the first that is
    defined — rather than an operator the evaluator has to model.

    Depth-tracked, so a `??` inside parentheses is not a split point. Nothing in
    the shipped convention needs that, and an interpreter that quietly did the
    wrong thing on an expression a deployment is free to write is worse than one
    that handles the general case.
    """
    parts: list[str] = []
    depth = 0
    start = 0
    index = 0
    while index < len(expression):
        char = expression[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and expression.startswith(COALESCE, index):
            parts.append(expression[start:index])
            index += len(COALESCE)
            start = index
            continue
        index += 1
    parts.append(expression[start:])
    return tuple(part.strip() for part in parts if part.strip())


def _evaluate(node: ast.AST, resolve: Any) -> Figure:
    """Evaluate ONE arithmetic node against a name resolver.

    **The grammar is closed and anything outside it raises.** Names, numeric
    constants, unary minus and the four binary operators — nothing else. This
    is an interpreter reading a Control Plane artifact, so an expression that
    reached a call, an attribute or a comprehension would be a deployment
    executing arbitrary code out of its own configuration. Refusing by default
    is the only safe posture, and `ValueError` names the node it refused.

    **Undefined propagates and never defaults.** A missing operand makes the
    whole expression undefined, which the caller serves as `NOT_EVALUABLE`. It
    is never zero: a leverage of 0 reads as a company with no debt, which is a
    different and false statement from "this could not be computed."
    """
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, resolve)
    if isinstance(node, ast.Name):
        return cast(Figure, resolve(node.id))
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"a ratio expression may not carry {node.value!r}")
        return Figure(amount=Decimal(str(node.value)), consumed=frozenset())
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _evaluate(node.operand, resolve)
        return Figure(
            amount=None if operand.amount is None else -operand.amount,
            consumed=operand.consumed,
        )
    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left, resolve)
        right = _evaluate(node.right, resolve)
        consumed = left.consumed | right.consumed
        if left.amount is None or right.amount is None:
            return Figure(amount=None, consumed=consumed)
        if isinstance(node.op, ast.Add):
            return Figure(left.amount + right.amount, consumed)
        if isinstance(node.op, ast.Sub):
            return Figure(left.amount - right.amount, consumed)
        if isinstance(node.op, ast.Mult):
            return Figure(left.amount * right.amount, consumed)
        if isinstance(node.op, ast.Div):
            # A zero denominator is UNDEFINED, not an exception and not
            # infinity. An obligor with no EBITDA has no leverage ratio; that
            # is a real and common state, not an error in the run.
            if right.amount == 0:
                return Figure(amount=None, consumed=consumed)
            return Figure(left.amount / right.amount, consumed)
    raise ValueError(
        f"a ratio expression may not contain {type(node).__name__}"
    )


def _figure(expression: str, resolve: Any) -> Figure:
    """The first defined alternative of a `??` chain, or undefined.

    The consumed set is the WINNING alternative's alone. A fallback that was
    evaluated and rejected consumed nothing the payload should claim to have
    used, and naming it would put a fact-cell in `inputs` that did not
    contribute to the number beside it.
    """
    last = UNDEFINED
    for alternative in _alternatives(expression):
        figure = _evaluate(ast.parse(alternative, mode="eval"), resolve)
        if figure.evaluable:
            return figure
        last = figure
    return last


# ---------------------------------------------------------------------------
# The spread itself — fact-cells mapped onto declared lines, period by period.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpreadLine:
    """One line of the spread for one period — reported or derived, never both.

    A REPORTED line is backed by a `FactCell` and carries that filing's own
    `accession`, `filed_date`, `basis_applied` and restatement marking. A
    DERIVED line has no filing of its own and carries `inputs` instead: the
    fact-cells this period's arithmetic consumed.

    `value is None` means `NOT_EVALUABLE` and is served as that word. It is
    never rendered `0` — §C.4 trap 5 and gate `OFS-G08`.
    """

    name: str
    declared_kind: str
    unit: str | None
    cell: FactCell | None
    value: Decimal | None
    inputs: tuple[str, ...]
    derived: bool

    @property
    def evaluable(self) -> bool:
        return self.value is not None

    @property
    def kind_conflict(self) -> bool:
        """The filer filed this line the other way round from its declaration.

        `InterestExpenseDebt` is the one tag in this estate filed BOTH as an
        instant and as a duration. The declaration calls the line a duration
        because an interest charge is a flow; an instant-filed instance is
        admitted with its own `period_start` and MARKED HERE, never silently
        reinterpreted into the shape the declaration expected.
        """
        if self.cell is None:
            return False
        filed_kind = KIND_INSTANT if self.cell.is_instant else "duration"
        return filed_kind != self.declared_kind


@dataclass(frozen=True)
class SpreadPeriod:
    """One column of the spread: every declared line at one fiscal period.

    **The key is `(period_end, fiscal_period)` and not `period_end`.** A single
    period end carries both — Digital Turbine's 2026-03-31 holds an `FY` cell
    and a `Q1` cell — and collapsing them would put a full year's revenue in the
    same column as a quarter's. That is the classic spreading error on the time
    axis rather than the peer axis, and the key forecloses it exactly as the
    peer join key forecloses the other.
    """

    period_end: date
    fiscal_period: str
    lines: Mapping[str, SpreadLine]
    latest_filed: date | None

    @property
    def signal_class(self) -> str:
        """Which λ_c this column's facts decay against — §E.1.

        This is where "the half-life is per signal class, not per product"
        stops being a sentence: two columns of the same payload return
        different values here, so one product carries two decay rates at once.
        """
        return (
            SIGNAL_ANNUAL
            if self.fiscal_period == FISCAL_ANNUAL
            else SIGNAL_QUARTERLY
        )

    @property
    def restated_lines(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, line in self.lines.items()
            if line.cell is not None and line.cell.restated
        )


def _reported_lines(
    cells: Sequence[FactCell], tag_map: Mapping[str, Any]
) -> dict[str, FactCell | None]:
    """Map this period's fact-cells onto declared lines BY TAG PRECEDENCE.

    An obligor commonly carries two or three tags for one line across its
    history as US-GAAP tagging changed, so each line declares an ORDERED list
    and **the first tag present wins**. The order is measured obligor coverage,
    not preference: the mapping degrades toward the commonest vocabulary rather
    than toward the author's taste.

    A line whose declared tags are ALL absent maps to `None` — one of the 50
    obligors carries none of the four revenue tags, and its revenue line is
    served `NOT_EVALUABLE` rather than `0`.
    """
    by_tag: dict[str, FactCell] = {}
    for cell in cells:
        # First wins within a tag too: `_read_cells` has already reduced each
        # fact-cell to one row under the requested basis, so a second row for
        # the same tag is a different `unit` — a currency artifact (§C.4 trap
        # 1), not a second opinion about the same figure.
        by_tag.setdefault(cell.tag, cell)
    resolved: dict[str, FactCell | None] = {}
    for name, declaration in tag_map.items():
        resolved[name] = next(
            (by_tag[tag] for tag in declaration[KEY_TAGS] if tag in by_tag), None
        )
    return resolved


def _derive_period(
    reported: Mapping[str, FactCell | None], ratios: Mapping[str, Any]
) -> dict[str, Figure]:
    """Resolve every declared ratio for one period, recursively and once each.

    Ratios name other ratios — `leverage` reads `total_debt` and `ebitda`, both
    themselves derived — so resolution follows the dependency graph rather than
    the artifact's declaration order. **Relying on declaration order would
    work today and break silently** the first time a deployment reorders its own
    YAML, which is a file it is invited to edit.

    A cycle raises rather than recursing forever, naming the chain.
    """
    memo: dict[str, Figure] = {}
    resolving: list[str] = []

    def resolve(name: str) -> Figure:
        if name in reported:
            cell = reported[name]
            if cell is None or cell.value is None:
                return UNDEFINED
            return Figure(amount=cell.value, consumed=frozenset({name}))
        if name not in ratios:
            # A name in no declaration is undefined, not an error: a deployment
            # may declare a ratio over a line it has not mapped, and the honest
            # answer is NOT_EVALUABLE.
            return UNDEFINED
        if name in memo:
            return memo[name]
        if name in resolving:
            chain = " -> ".join([*resolving, name])
            raise ValueError(f"ratio definitions form a cycle: {chain}")
        resolving.append(name)
        try:
            figure = _figure(str(ratios[name][KEY_EXPRESSION]), resolve)
        finally:
            resolving.pop()
        memo[name] = figure
        return figure

    return {name: resolve(name) for name in ratios}


def _spread(
    cells: Sequence[FactCell], convention: Mapping[str, Any]
) -> tuple[SpreadPeriod, ...]:
    """Every fact-cell arranged into the declared lines, newest period first."""
    tag_map = convention[KEY_TAG_MAP]
    ratios = convention[KEY_RATIOS]

    grouped: dict[tuple[date, str], list[FactCell]] = defaultdict(list)
    for cell in cells:
        grouped[(cell.period_end, cell.fiscal_period)].append(cell)

    periods: list[SpreadPeriod] = []
    for (period_end, fiscal_period), period_cells in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1]), reverse=True
    ):
        reported = _reported_lines(period_cells, tag_map)
        derived = _derive_period(reported, ratios)
        lines: dict[str, SpreadLine] = {
            name: SpreadLine(
                name=name,
                declared_kind=str(tag_map[name][KEY_KIND]),
                unit=cell.unit if cell is not None else None,
                cell=cell,
                value=cell.value if cell is not None else None,
                inputs=(),
                derived=False,
            )
            for name, cell in reported.items()
        }
        for name, figure in derived.items():
            lines[name] = SpreadLine(
                name=name,
                declared_kind=str(ratios[name].get(KEY_UNIT, "")),
                unit=str(ratios[name][KEY_UNIT]),
                cell=None,
                value=figure.amount,
                # Sorted so the payload is byte-stable: a `frozenset` iterates
                # in an order that is not guaranteed across runs, and an
                # unstable ordering here would change the content address
                # without changing a single figure.
                inputs=tuple(sorted(figure.consumed)),
                derived=True,
            )
        filed = [cell.filed_date for cell in period_cells if cell.filed_date]
        periods.append(
            SpreadPeriod(
                period_end=period_end,
                fiscal_period=fiscal_period,
                lines=lines,
                latest_filed=max(filed) if filed else None,
            )
        )
    return tuple(periods)


# ---------------------------------------------------------------------------
# The question, and the one read that answers it.
# ---------------------------------------------------------------------------


def request(
    *, parameters: Mapping[str, object], asked_at: datetime | None = None
) -> ProductRequest:
    """Build the typed question from the caller's parameters and this
    deployment's declared vocabulary.

    The address tokens come from `artifacts/question.yaml` and the class
    identity from `ccf_config.yaml`. `parameters` is the CALLER'S — this
    function supplies no value for it and no default, which is what keeps the
    contract's requirement real (§B.4).
    """
    question_declaration = question()
    declared = config()[KEY_PRODUCT_CLASS]
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=question_declaration["subject"],
        intent=question_declaration["parameters"][PARAM_INTENT],
        freshness=question_declaration["freshness"],
        asked_at=asked_at
        or datetime.fromisoformat(question_declaration["asked_at"]),
        parameters=parameters,
    )


def demonstration_parameters() -> Mapping[str, Any]:
    """The bundled demonstration's request parameters — §B.4, all defaulted."""
    return cast(Mapping[str, Any], question()["parameters"])


def demonstration_anchor() -> str:
    """The anchor the bundled demonstration asks about, from scenario material.

    **Nothing in this module names an LEI.** `make example-cp-03 LEI=<other>`
    re-asks the same question of another obligor, and the anchor is swappable
    because it lives in an artifact rather than here.
    """
    return str(question()["subject"])


def unsupported_arguments() -> Mapping[str, str]:
    """Parameters this tier DECLARES and always REFUSES — §B.5, `OFS-G06`.

    Read from `ccf_config.yaml`'s `request_contract:` block, never listed here:
    a parameter this deployment stops supporting, or starts, is a change to that
    document and not to this module.
    """
    declared = config()[KEY_REQUEST_CONTRACT]
    return cast(Mapping[str, str], declared.get("unsupported_arguments", {}))


def declared_ttl_seconds() -> int:
    return int(ttl_declaration()["declared_ttl_seconds"])


def max_ttl_seconds() -> int:
    return int(ttl_declaration()["max_ttl_seconds"])


def source_read(
    tenant: str,
    *,
    at: datetime,
    subject: str,
    principal_id: str,
    periods: int,
    basis: str,
    include_peers: bool,
) -> SourceRead:
    """Read the system of record once — §D.2 steps 1, 3 and 4.

    **THE THREE READS ARE NOT ONE READ, and they are not three round trips per
    period either.** Resolution goes through rung 01's crosswalk; the facts are
    ONE batched select for all periods and all tags; peers are a separate
    conditional read joined on `period_end`. Three statements on one connection.

    **One envelope, and the reason is worth stating rather than assuming.** The
    obvious alternative — one envelope per signal class, so `annual_facts` and
    `quarterly_facts` carry their own `observed_time` — does not survive
    contact with L2: all four would share this product's single `match_key`, so
    the idempotent upsert merges them into ONE entity and the last write wins on
    `spread_periods`. The payload would silently become whichever class was
    ingested last.

    So the entity carries the whole spread, and **per-attribute temporal
    validity lives where §A says it lives — on the attributes**: every period
    keeps its own `filed_date` and every fact-cell its own `accession`. That is
    what `SpreadScenario.debt` reads to produce two decay rates from one
    product, and it is the honest shape given §D.7.1's finding that the SDK
    imposes no general per-attribute lineage obligation.

    The read is `SELECT`-only. Nothing this function runs writes to the store.
    """
    threshold = Decimal(str(restatement_rule()["material_threshold"]))
    with psycopg.connect(source_dsn()) as db:
        with db.cursor() as cur:
            resolved = _resolve_obligor(cur, subject)
            # The policy step runs BEFORE any fact is read (composition
            # invariant 1), so the grant is resolved even where the anchor
            # resolved to nothing — a 404 and a 403 are different refusals and
            # the caller is owed the right one.
            permitted = _permitted_jurisdictions(cur, principal_id=principal_id)
            if resolved is None:
                return SourceRead(
                    resolved=None,
                    cells=(),
                    peers=(),
                    permitted_jurisdictions=permitted,
                    envelopes=(),
                )
            cells = _read_cells(
                cur, subject, periods=periods, basis=basis, threshold=threshold
            )
            peers = (
                _read_peers(
                    cur,
                    sic=_obligor_sic(cur, subject),
                    period_ends=tuple(
                        sorted({cell.period_end for cell in cells}, reverse=True)
                    ),
                    exclude_cik=resolved.cik,
                )
                if include_peers
                else ()
            )

    spread = _spread(cells, spreading_convention())
    filed = [
        period.latest_filed for period in spread if period.latest_filed is not None
    ]
    envelope = SignalEnvelope(
        tenant_id=tenant,
        envelope_id=f"spread:{resolved.lei}:{basis}",
        source=SourceIdentity(system_id=TABLE_FACT),
        # The request instant, so the as-of boundary the caller asked at is at
        # or after the claim's `observed_at`.
        ingestion_timestamp=at,
        # THE LATEST FILING THE PAYLOAD CONSUMED — `ttl.yaml`'s declared
        # `latest_filed_date_in_payload`, and NOT a wall clock. A spread built
        # from a 10-K filed 2026-08-05 is 24 days old whichever instant it was
        # asked at, and this is the column that makes that true.
        observed_time=_instant(max(filed)) if filed else at,
        raw_payload={
            ATTR_MATCH_KEY: resolved.lei,
            ATTR_LEI: resolved.lei,
            ATTR_CIK: resolved.cik,
            ATTR_NAME: resolved.legal_name,
            ATTR_JURISDICTION: resolved.jurisdiction,
            ATTR_FY_END_MONTH: resolved.fiscal_year_end_month,
            ATTR_LATEST_FILED: max(filed).isoformat() if filed else None,
            ATTR_FORMALLY_RESTATED: resolved.has_non_reliance_filing,
            ATTR_PERIODS: len(spread),
            ATTR_PEERS: len({peer.cik for peer in peers}),
        },
    )
    return SourceRead(
        resolved=resolved,
        cells=cells,
        peers=peers,
        permitted_jurisdictions=permitted,
        envelopes=(envelope,),
    )


def _obligor_sic(cur: Any, anchor: str) -> str | None:
    """The anchor's SIC — the cohort key `peer_basis: sic` selects on.

    Read from `legal_entity` rather than from `peer_entity`: the anchor is an
    obligor, not a peer, and this estate keeps the two populations in different
    tables. An obligor whose SIC matches no peer row is PEERLESS, which
    `_read_peers` degrades on rather than refusing.
    """
    cur.execute(
        f"select sic from {SOURCE_SCHEMA}.{TABLE_ENTITY} where lei = %s", (anchor,)
    )
    row = cur.fetchone()
    return _text(row[0]) if row else None


# ---------------------------------------------------------------------------
# The scenario — this deployment's answers to everything the spine asks for.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpreadScenario:
    """This deployment's answers to what the spine asks for."""

    envelopes: tuple[SignalEnvelope, ...]
    request: ProductRequest
    request_contract: ProductRequestContract
    product_class: ProductClassDeclaration
    perspective: PerspectiveArtifact
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    resolution: EntityResolutionSpec
    half_life_table: HalfLifeTable
    debt_profile: DebtProfile
    resolved: ResolvedObligor
    periods: tuple[SpreadPeriod, ...]
    peers: tuple[PeerFact, ...]
    permitted_jurisdictions: tuple[str, ...]
    basis: str
    ttl_seconds: int
    max_ttl_seconds: int
    halflife_debt_profile: str

    request_contract_key: str = KEY_REQUEST_CONTRACT
    policy_bundle_key: str = KEY_POLICY_BUNDLE
    replay_record_class: str = REPLAY_RECORD_CLASS
    query_pin_class: str = QUERY_PIN_CLASS
    artifact_store_dirname: str = ARTIFACT_STORE_DIRNAME

    @property
    def plan_id(self) -> str:
        return self.product_class.schema_name

    @property
    def temporal_boundary(self) -> datetime:
        """Off the request, never off a clock — so replay feeds it back."""
        return self.request.asked_at

    @property
    def now(self) -> datetime:
        return self.request.asked_at

    @property
    def latest_filed_in_payload(self) -> date | None:
        """The freshest filing any served figure rests on — the TTL anchor.

        `ttl.yaml` declares `ttl_anchor_basis: latest_filed_date_in_payload`,
        and the choice between `latest` and `earliest` is a real decision the
        artifact makes rather than a detail: `latest` says the payload is as
        fresh as its FRESHEST claim, which is optimistic — a spread carrying one
        current quarter and four stale annuals looks fresh. `OFS-G09` asserts
        the shipped behavior and is written to turn RED if the declaration is
        changed to `earliest`. That redness is the signal to reopen §F.4
        finding 4; it is not a regression.
        """
        filed = [
            period.latest_filed
            for period in self.periods
            if period.latest_filed is not None
        ]
        return max(filed) if filed else None

    @property
    def expires_at(self) -> datetime:
        """The declared TTL applied to the anchor the class names.

        `ttl_anchor: from_entity_freshness`, and for this product the entity's
        freshness IS its latest filing — an observation timestamp that MOVES,
        because filers file quarterly. §E.1.1 is the whole argument: rung 02
        anchors on a date that can never advance and refuses 50 of 60
        permanently; this rung refuses 27 of 50 and those clear as filers file.
        Same primitive, opposite behavior, and the difference is entirely
        whether the anchored field is re-observed.
        """
        anchor = self.latest_filed_in_payload
        base = _instant(anchor) if anchor is not None else self.now
        return base + timedelta(seconds=self.ttl_seconds)

    def _observations(self) -> tuple[Observation, ...]:
        """One observation per spread period, TYPED BY THAT PERIOD'S CLASS.

        **This is where §E.1 stops being a table.** An annual column decays
        against `annual_facts` (~365d) and a quarterly column against
        `quarterly_facts` (~90d), so one payload carries two decay rates at
        once — which a single product-level `λ_c` could not express, and which
        is the whole reason the half-life table is keyed per signal class.

        Dated from the period's OWN latest filing, not from the payload's. A
        four-year-old annual is four years stale even in a spread whose newest
        quarter landed last week, and averaging the two would launder exactly
        the staleness a credit officer needs to see.
        """
        return tuple(
            Observation(
                observation_type=period.signal_class,
                observed_at=_instant(period.latest_filed),
                subject=f"{self.resolved.lei}:{period.period_end}:{period.fiscal_period}",
            )
            for period in self.periods
            if period.latest_filed is not None
        )

    def _completeness(self) -> Decimal:
        """The fraction of declared lines this payload could actually evaluate.

        Every `NOT_EVALUABLE` line is a real shortfall and contributes its full
        weight — §E.2 names three of them: a missing revenue line, a missing
        peer cohort, and ratio inputs incomplete. None is filled with a default,
        so the score is the honest count of what the estate did not carry.
        """
        lines = [line for period in self.periods for line in period.lines.values()]
        if not lines:
            return Decimal(0)
        evaluable = sum(1 for line in lines if line.evaluable)
        return Decimal(evaluable) / Decimal(len(lines))

    def debt(self) -> DebtAssessment:
        """`D_c` over what this question assembled — whitepaper §7.7, spec §E.2.

        **`S` is 1 and it is a MEASURED PROPERTY of this estate, not a magic
        constant.** Semantic consistency is disagreement between sources about
        the same fact, and this product reads ONE store: `financial_fact` is the
        only authority for a figure, and `peer_fact` describes different
        companies rather than the same one. **Nothing here could disagree**, so
        the signal cannot fire, and an `S` of 1 that no data could have moved is
        recorded as a structural property rather than presented as agreement.
        """
        observations = self._observations()
        if not observations:
            # `FreshnessScorer` refuses an empty sequence by design. An empty
            # spread is a fail-closed condition (§D.2 step 3 -> 404), not a debt
            # reading, so this returns the maximum rather than inventing a score
            # for nothing.
            return assess_debt(
                DebtFactors(
                    freshness=Decimal(0),
                    completeness=Decimal(0),
                    semantic_consistency=Decimal(1),
                ),
                profile=self.debt_profile,
            )
        scorer = FreshnessScorer(
            table=self.half_life_table,
            risk_sensitivity=self.debt_profile.risk_sensitivity,
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(observations, now=self.now),
                completeness=self._completeness(),
                semantic_consistency=Decimal(1),
            ),
            profile=self.debt_profile,
        )


def read(
    booted: BootedFabric,
    asked: ProductRequest,
    *,
    principal_id: str | None = None,
) -> SpreadScenario | None:
    """Name this deployment's artifact keys and read this question's values.

    Returns `None` when the anchor resolves to nothing, or resolves to an
    obligor with no facts — §D.2's fail-closed `404`. *"An anchor that resolves
    to no entity is never an empty payload."* The caller renders the refusal;
    this function does not invent an empty scenario to keep a happy path alive.
    """
    artifacts = booted.artifacts
    parameters = asked.parameters
    declared_perspective = cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE])
    # The SAME question asked by two principals is two different answers —
    # §B.2's entitlement leg suppresses 49/47/0/0 across the six principal
    # pairs. The default is the declared perspective; an override is how the
    # demonstration and gate `OFS-G15` ask it as somebody else, and it changes
    # WHICH OBLIGORS EXIST rather than how they are shaped.
    if principal_id is not None and principal_id != declared_perspective.principal_id:
        declared_perspective = declared_perspective.model_copy(
            update={"principal_id": principal_id}
        )

    basis = str(parameters.get(PARAM_BASIS, BASIS_AS_REPORTED))
    read_source = source_read(
        booted.tenant_id,
        at=asked.asked_at,
        subject=asked.subject,
        principal_id=declared_perspective.principal_id,
        periods=int(parameters[PARAM_PERIODS]),
        basis=basis,
        include_peers=bool(parameters.get(PARAM_INCLUDE_PEERS, False)),
    )
    if read_source.resolved is None or not read_source.cells:
        return None

    # The policy parameters are built PER REQUEST from the calling principal's
    # grant set, never taken statically from the config. A static allowlist
    # would serve one principal's obligors to every principal — a correctness
    # defect that presents intermittently. The declared artifact supplies the
    # SHAPE; the estate supplies this principal's values.
    declared_policy = cast(OperatorParametersArtifact, artifacts[KEY_POLICY_OPERATOR])
    policy_parameters = declared_policy.model_copy(
        update={
            "permitted_classifications": tuple(read_source.permitted_jurisdictions)
        }
    )

    return SpreadScenario(
        envelopes=read_source.envelopes,
        resolved=read_source.resolved,
        periods=_spread(read_source.cells, spreading_convention()),
        peers=read_source.peers,
        permitted_jurisdictions=read_source.permitted_jurisdictions,
        basis=basis,
        request=asked,
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=declared_perspective,
        # ONE entry, so one operator. The spine never counts them, and
        # `OFS-G10` asserts the count is exactly one and that no operator whose
        # key or category is `Enrich` is registered.
        operator_parameters={KEY_POLICY_OPERATOR: policy_parameters},
        resolution=cast(EntityResolutionSpec, artifacts[KEY_RESOLUTION]),
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
        ttl_seconds=declared_ttl_seconds(),
        max_ttl_seconds=max_ttl_seconds(),
        # A pinned reference, never the resolved artifact: the profile has its
        # own version lane, and inlining it would give one record two version
        # identities.
        halflife_debt_profile=(
            f"ccf-artifact://{booted.tenant_id}/ccf.debt-profile/"
            f"{KEY_DEBT_PROFILE}@{booted.pins.version_for(KEY_DEBT_PROFILE)}"
        ),
    )
