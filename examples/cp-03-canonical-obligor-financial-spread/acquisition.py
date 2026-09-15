"""The one source leg, and the arithmetic over what it returned — nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**, which is the clearest statement of what it is: somebody else's store,
read the way that store wants to be read, and a declared convention interpreted
over the rows. It opens one system of record, resolves the anchor through the
crosswalk, reads every fact-cell in one windowed query, reads the peer cohort
at the anchor's own period ends, and hands back what it found arranged into the
declared lines.

**Its boundaries are ruled, not stylistic** (`D-IMPL-315`). This layer handles
*vocabulary, source access and admission*. It binds no request value onto a
Control Plane declaration, runs no gate, builds no replay record and serves
nothing. Those belong to `GovernedResolver`, which `produce.py` hands the seam
to; a helpful local shortcut here is the exact defect the successor exists not
to have.

**The business meaning is the frozen specimen's, re-expressed** (`CP14-F-22`):
resolution goes THROUGH the crosswalk and never reads `financial_fact.cik`; the
basis selects WITHIN a fact-cell and never across cells; a restatement is a
distinct value across accessions on the estate's own identity key and never an
accession count; a spread column is keyed `(period_end, fiscal_period)` and
never by `period_end` alone; a peer is matched at an IDENTICAL `period_end` and
never at an identical filing date; `NOT_EVALUABLE` is a word and never a zero;
and a derived line names the lines its arithmetic ACTUALLY read, which for a
`??` fallback is one branch and not the declared union.

**Three SELECTs, never one per period or per tag** (§7.4 N+1 avoidance).
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import psycopg
import yaml

HERE = Path(__file__).parent

#: The word served where a figure cannot be evaluated. Never `0`.
NOT_EVALUABLE = "NOT_EVALUABLE"

#: The two bases a caller may ask for. The values are the request contract's.
BASIS_AS_REPORTED = "as-reported"
BASIS_LATEST_RESTATED = "latest-restated"

#: The declared-fallback operator in a ratio expression: `a ?? b` takes `a`
#: where it is defined and `b` otherwise. Not Python, so the expression is
#: split on it before parsing — see `_alternatives`.
COALESCE = "??"

#: Signal classes a spread column decays against — the `half_life` keys.
SIGNAL_ANNUAL = "annual_facts"
SIGNAL_QUARTERLY = "quarterly_facts"

CLASS_PRECISION = "precision"
CLASS_MATERIAL = "material"
KIND_INSTANT = "instant"
KIND_DURATION = "duration"

#: The one source binding `backends.yaml` declares.
SOURCE = "financial_spread"


# ---------------------------------------------------------------------------
# The deployment's own documents, read here and nowhere else in this module.
# ---------------------------------------------------------------------------


def _document(path: Path) -> Mapping[str, Any]:
    """One YAML document, parsed. The only file reading in this module."""
    parsed: Mapping[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed


def vocabulary() -> Mapping[str, Any]:
    """The source's own names — tables and the two fiscal markers."""
    declaration: Mapping[str, Any] = _document(
        HERE / "artifacts" / "source-vocabulary.yaml"
    )["declaration"]
    return declaration


def restatement_rule() -> Mapping[str, Any]:
    """The identity key and the threshold — never code constants."""
    declaration: Mapping[str, Any] = _document(
        HERE / "artifacts" / "restatement.yaml"
    )["declaration"]
    return declaration


def spreading_convention() -> Mapping[str, Any]:
    """Tag map, ratio definitions and adjustments."""
    declaration: Mapping[str, Any] = _document(
        HERE / "artifacts" / "spread-lines.yaml"
    )["declaration"]
    return declaration


def _schema(settings: Mapping[str, str]) -> str:
    """The namespace the seven tables live in — environment, never a literal.

    ``settings`` is the environment document's ``financial_spread`` block,
    resolved BY NAME once at open (``ccf_environment.yaml``; `D-IMPL-343`):
    this module holds no variable name, no remedy text and no default, and a
    deployment that quietly reached a different store than the one it names
    is refused before the first question rather than here.
    """
    schema = settings["schema"]
    if not schema.replace("_", "").isalnum():
        raise RuntimeError(f"the declared schema setting holds {schema!r}, which is not a bare schema name")
    return schema


# ---------------------------------------------------------------------------
# Value helpers. Each one exists because the source and the contract disagree
# about a representation, and the disagreement is resolved HERE.
# ---------------------------------------------------------------------------


def _text(value: Any) -> str | None:
    """A source value as text, or None when the source did not carry it."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: Any) -> Decimal | None:
    """A source numeric as `Decimal`, never as `float`.

    A float is not bit-stable across platforms, so it cannot be canonically
    encoded and cannot appear in a content address.
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
    `material`.
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
    fiscal_year_end_month: int | None
    latest_filed: date | None
    #: SEC 8-K Item 4.02 — the filer's own non-reliance declaration.
    #: CORROBORATION ONLY; it never detects a restatement.
    has_non_reliance_filing: bool
    sic: str | None


@dataclass(frozen=True)
class FactCell:
    """One fact-cell: the same fact as the estate's own key defines it."""

    tag: str
    unit: str
    period_start: date | None
    period_end: date
    fiscal_period: str
    value: Decimal | None
    accession: str
    filed_date: date
    form: str
    restated: bool
    restatement_class: str | None

    @property
    def is_instant(self) -> bool:
        """Balance-sheet facts carry no `period_start`."""
        return self.period_start is None


@dataclass(frozen=True)
class PeerFact:
    """One peer's figure, at a `period_end` IDENTICAL to one the anchor carries."""

    cik: int
    sic: str | None
    tag: str
    period_end: date
    value: Decimal | None
    filed_date: date | None


@dataclass(frozen=True)
class Figure:
    """A computed amount and THE FACT-CELL LINES IT ACTUALLY CONSUMED."""

    amount: Decimal | None
    consumed: frozenset[str]

    @property
    def evaluable(self) -> bool:
        return self.amount is not None


UNDEFINED = Figure(amount=None, consumed=frozenset())


@dataclass(frozen=True)
class SpreadLine:
    """One line of the spread for one period — reported or derived, never both."""

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
        """The filer filed this line the other way round from its declaration."""
        if self.cell is None:
            return False
        filed_kind = KIND_INSTANT if self.cell.is_instant else KIND_DURATION
        return filed_kind != self.declared_kind


@dataclass(frozen=True)
class SpreadPeriod:
    """One column of the spread: every declared line at one fiscal period.

    Keyed `(period_end, fiscal_period)` and not `period_end`: a single period
    end carries both an `FY` cell and a `Q1` cell for a non-December filer.
    """

    period_end: date
    fiscal_period: str
    lines: Mapping[str, SpreadLine]
    latest_filed: date | None

    def signal_class(self, *, fiscal_annual: str) -> str:
        """Which λ_c this column's facts decay against."""
        return SIGNAL_ANNUAL if self.fiscal_period == fiscal_annual else SIGNAL_QUARTERLY


@dataclass(frozen=True)
class CohortStatistic:
    """The cohort's shape for one tag at one period end — a closed description.

    Its lineage is *every peer in this SIC reporting this tag at this exact
    period_end*: restatable and re-executable, and deliberately weaker than a
    ratio line's enumerated inputs, which is why `peers_reporting` is served
    beside the figure.
    """

    period_end: date
    tag: str
    peers_reporting: int
    median: Decimal
    latest_filed: date | None


@dataclass(frozen=True)
class SpreadRead:
    """Everything one question needed from the store, read and shaped."""

    anchor_lei: str
    basis: str
    resolved: ResolvedObligor | None
    periods: tuple[SpreadPeriod, ...]
    cohort: tuple[CohortStatistic, ...]
    cohort_size: int
    cohort_basis: str

    @property
    def latest_filed_in_payload(self) -> date | None:
        """The freshest filing any served figure rests on — the declared anchor."""
        filed = [p.latest_filed for p in self.periods if p.latest_filed is not None]
        return max(filed) if filed else None


# ---------------------------------------------------------------------------
# The reads. Three, and they are deliberately not one.
# ---------------------------------------------------------------------------


def _resolve_obligor(cur: Any, schema: str, tables: Mapping[str, str], anchor: str, *, fiscal_annual: str, annual_form: str) -> ResolvedObligor | None:
    """Resolve the anchor THROUGH the crosswalk.

    `financial_fact` carries both `lei` and `cik`, so this product COULD resolve
    without the crosswalk. It must not: the authority for LEI→CIK is the
    crosswalk, and a product that read the local column would silently stop
    depending on its declared prerequisite. The `filing_profile` join is LEFT —
    most obligors have no Item 4.02 row, and their absence is a fact.
    """
    cur.execute(
        f"""
        select xw.lei, xw.cik,
               le.legal_name, le.legal_jurisdiction, le.sic,
               coalesce(fp.count_8k_item_4_02, 0) as non_reliance_filings,
               (select max(f.filed_date)
                  from {schema}.{tables['facts']} f
                 where f.lei = xw.lei) as latest_filed,
               (select extract(month from max(f.period_end))
                  from {schema}.{tables['facts']} f
                 where f.lei = xw.lei
                   and f.fiscal_period = %s and f.form = %s) as fy_end_month
          from {schema}.{tables['crosswalk']} xw
          join {schema}.{tables['entities']} le on le.lei = xw.lei
     left join {schema}.{tables['filing_profile']} fp on fp.lei = xw.lei
         where xw.lei = %s
        """,
        (fiscal_annual, annual_form, anchor),
    )
    row = cur.fetchone()
    if row is None:
        return None
    lei, cik, name, jurisdiction, sic, filings, latest, fy_month = row
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
        fiscal_year_end_month=int(fy_month) if fy_month is not None else None,
        latest_filed=latest,
        has_non_reliance_filing=int(filings) > 0,
        sic=_text(sic),
    )


def _read_cells(cur: Any, schema: str, tables: Mapping[str, str], anchor: str, *, periods: int, basis: str, threshold: Decimal, identity: Sequence[str]) -> tuple[FactCell, ...]:
    """ONE query for all periods and all tags.

    **THE BASIS SELECTS WITHIN A CELL, NOT ACROSS CELLS.** `as-reported` takes
    the EARLIEST accession for each fact-cell; `latest-restated` takes the
    latest. Both return one row per cell.

    **THE PARTITION IS THE ARTIFACT'S KEY, NOT A CONSTANT.** `lei` is the WHERE
    filter rather than a partition column, so it is the one key member absent.
    The restatement flag and its class are computed in the same pass, from the
    first- and last-filed values of the cell.
    """
    order = "asc" if basis == BASIS_AS_REPORTED else "desc"
    partition = ", ".join(f"f.{column}" for column in identity if column != "lei")
    cur.execute(
        f"""
        with ranked as (
            select f.tag, f.unit, f.period_start, f.period_end, f.fiscal_period,
                   f.value, f.accession, f.filed_date, f.form,
                   min(f.value) over w                              as min_value,
                   max(f.value) over w                              as max_value,
                   first_value(f.value)      over (partition by {partition}
                                                   order by f.filed_date asc)  as first_value,
                   first_value(f.value)      over (partition by {partition}
                                                   order by f.filed_date desc) as last_value,
                   row_number()              over (partition by {partition}
                                                   order by f.filed_date {order},
                                                            f.accession {order}) as pick
              from {schema}.{tables['facts']} f
             where f.lei = %s
            window w as (partition by {partition})
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
        (tag, unit, p_start, p_end, fiscal, value, accession, filed, form, restated, first_v, last_v) = row
        restated = bool(restated)
        klass: str | None = None
        if restated:
            change = _relative_change(_decimal(first_v), _decimal(last_v))
            klass = NOT_EVALUABLE if change is None else (CLASS_MATERIAL if change >= threshold else CLASS_PRECISION)
        cells.append(
            FactCell(
                tag=str(tag), unit=str(unit), period_start=p_start, period_end=p_end,
                fiscal_period=str(fiscal), value=_decimal(value), accession=str(accession),
                filed_date=filed, form=str(form), restated=restated, restatement_class=klass,
            )
        )
    return tuple(cells)


def _read_peers(cur: Any, schema: str, tables: Mapping[str, str], *, sic: str | None, period_ends: Sequence[date], exclude_cik: int) -> tuple[PeerFact, ...]:
    """The peer cohort's facts at the anchor's own period ends.

    **Degrades, never fails.** A cohort of nobody is a legitimate answer. There
    is no `filed_date` in the join and that is not an omission: matching peers
    on filing date compares a Q3 figure to a peer's Q2 because the two filed
    the same week, and the join key forecloses it structurally.
    """
    if sic is None or not period_ends:
        return ()
    cur.execute(
        f"""
        select pf.cik, pe.sic, pf.tag, pf.period_end, pf.value, pf.filed_date
          from {schema}.{tables['peer_facts']} pf
          join {schema}.{tables['peer_entities']} pe on pe.cik = pf.cik
         where pe.sic = %s
           and pf.cik <> %s
           and pf.period_end = any(%s)
         order by pf.period_end desc, pe.cik, pf.tag
        """,
        (sic, exclude_cik, list(period_ends)),
    )
    return tuple(
        PeerFact(cik=int(r[0]), sic=_text(r[1]), tag=str(r[2]), period_end=r[3], value=_decimal(r[4]), filed_date=r[5])
        for r in cur.fetchall()
    )


def grant_for(principal_id: str, *, settings: Mapping[str, str]) -> tuple[str, ...]:
    """The principal's jurisdiction grant, EXPANDED against the estate.

    A principal is granted a PREFIX — `US` reaches `US-DE`, `US-MD`, `US-NV`.
    The policy operator tests EXACT membership, so a prefix handed to it
    unexpanded matches nothing and empties the view. The expansion is
    therefore the deployment's, against the jurisdictions the estate actually
    holds, and the value it produces is what a caller states as the request's
    `jurisdictions` — a request parameter that survives governance and lands
    in replay, never a value written over a resolved artifact.
    """
    schema, tables = _schema(settings), vocabulary()["tables"]
    with psycopg.connect(settings["dsn"]) as db, db.cursor() as cur:
        cur.execute(
            f"""
            select distinct le.legal_jurisdiction
              from {schema}.{tables['entities']} le
              join {schema}.{tables['principal_jurisdictions']} pj
                on le.legal_jurisdiction = pj.jurisdiction_prefix
                or le.legal_jurisdiction like pj.jurisdiction_prefix || '-%%'
             where pj.principal_id = %s
               and le.legal_jurisdiction is not null
            """,
            (principal_id,),
        )
        return tuple(sorted(str(row[0]) for row in cur.fetchall()))


# ---------------------------------------------------------------------------
# Derivation — an INTERPRETER over the declared convention. Algorithmic, and no
# LLM is reachable from it.
# ---------------------------------------------------------------------------


def _alternatives(expression: str) -> tuple[str, ...]:
    """Split a ratio expression on its TOP-LEVEL `??` fallbacks, depth-tracked."""
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
    constants, unary minus and the four binary operators — nothing else.
    **Undefined propagates and never defaults.** A zero denominator is
    UNDEFINED, not an exception and not infinity.
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
        return Figure(amount=None if operand.amount is None else -operand.amount, consumed=operand.consumed)
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
            if right.amount == 0:
                return Figure(amount=None, consumed=consumed)
            return Figure(left.amount / right.amount, consumed)
    raise ValueError(f"a ratio expression may not contain {type(node).__name__}")


def _figure(expression: str, resolve: Any) -> Figure:
    """The first defined alternative of a `??` chain, or undefined.

    The consumed set is the WINNING alternative's alone.
    """
    last = UNDEFINED
    for alternative in _alternatives(expression):
        figure = _evaluate(ast.parse(alternative, mode="eval"), resolve)
        if figure.evaluable:
            return figure
        last = figure
    return last


def _reported_lines(cells: Sequence[FactCell], tag_map: Mapping[str, Any]) -> dict[str, FactCell | None]:
    """Map this period's fact-cells onto declared lines BY TAG PRECEDENCE."""
    by_tag: dict[str, FactCell] = {}
    for cell in cells:
        by_tag.setdefault(cell.tag, cell)
    return {
        name: next((by_tag[tag] for tag in declaration["tags"] if tag in by_tag), None)
        for name, declaration in tag_map.items()
    }


def _derive_period(reported: Mapping[str, FactCell | None], ratios: Mapping[str, Any]) -> dict[str, Figure]:
    """Resolve every declared ratio for one period, recursively and once each.

    Resolution follows the dependency graph rather than the artifact's
    declaration order; a cycle raises rather than recursing forever.
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
            return UNDEFINED
        if name in memo:
            return memo[name]
        if name in resolving:
            raise ValueError("ratio definitions form a cycle: " + " -> ".join([*resolving, name]))
        resolving.append(name)
        try:
            figure = _figure(str(ratios[name]["expression"]), resolve)
        finally:
            resolving.pop()
        memo[name] = figure
        return figure

    return {name: resolve(name) for name in ratios}


def spread(cells: Sequence[FactCell], convention: Mapping[str, Any]) -> tuple[SpreadPeriod, ...]:
    """Every fact-cell arranged into the declared lines, newest period first."""
    tag_map = convention["tag_map"]
    ratios = convention["ratios"]
    grouped: dict[tuple[date, str], list[FactCell]] = defaultdict(list)
    for cell in cells:
        grouped[(cell.period_end, cell.fiscal_period)].append(cell)
    periods: list[SpreadPeriod] = []
    for (period_end, fiscal_period), period_cells in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1]), reverse=True):
        reported = _reported_lines(period_cells, tag_map)
        derived = _derive_period(reported, ratios)
        lines: dict[str, SpreadLine] = {
            name: SpreadLine(
                name=name, declared_kind=str(tag_map[name]["kind"]),
                unit=cell.unit if cell is not None else None, cell=cell,
                value=cell.value if cell is not None else None, inputs=(), derived=False,
            )
            for name, cell in reported.items()
        }
        for name, figure in derived.items():
            lines[name] = SpreadLine(
                name=name, declared_kind=str(ratios[name].get("unit", "")), unit=str(ratios[name]["unit"]),
                cell=None, value=figure.amount,
                # Sorted so the payload is byte-stable: a frozenset iterates in
                # an order not guaranteed across runs.
                inputs=tuple(sorted(figure.consumed)), derived=True,
            )
        filed = [cell.filed_date for cell in period_cells if cell.filed_date]
        periods.append(SpreadPeriod(period_end=period_end, fiscal_period=fiscal_period, lines=lines, latest_filed=max(filed) if filed else None))
    return tuple(periods)


def _median(values: Sequence[Decimal]) -> Decimal:
    """The middle value, averaging the two middles on an even count — in Decimal."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def cohort_statistics(peers: Sequence[PeerFact]) -> tuple[CohortStatistic, ...]:
    """The cohort's shape per (period_end, tag) — an aggregate, never the rows.

    This estate's largest SIC cohort holds hundreds of peers and thousands of
    facts; emitting them as rows would be a data dump. The median's lineage is
    a closed description, and the reporting count is served beside it so a
    median over three peers and one over three hundred can be told apart.
    """
    values: dict[tuple[date, str], list[Decimal]] = defaultdict(list)
    filed: dict[tuple[date, str], list[date]] = defaultdict(list)
    for peer in peers:
        key = (peer.period_end, peer.tag)
        if peer.value is not None:
            values[key].append(peer.value)
        if peer.filed_date is not None:
            filed[key].append(peer.filed_date)
    return tuple(
        CohortStatistic(period_end=period_end, tag=tag, peers_reporting=len(group), median=_median(group), latest_filed=max(filed[(period_end, tag)]) if filed[(period_end, tag)] else None)
        for (period_end, tag), group in sorted(values.items(), key=lambda item: (item[0][0], item[0][1]), reverse=True)
    )


# ---------------------------------------------------------------------------
# The one read that answers one question.
# ---------------------------------------------------------------------------


def acquire(*, anchor_lei: str, periods: int, basis: str, include_peers: bool, peer_basis: str, settings: Mapping[str, str]) -> SpreadRead:
    """Read the system of record once and arrange what it returned.

    Returns a read whose `resolved` is `None` when the anchor resolves to no
    entity, or to one with no facts. The caller ingests nothing for it and the
    governed path refuses it — this function invents no empty scenario to keep
    a happy path alive, and it raises nothing for a question that merely has no
    answer.

    The read is `SELECT`-only. Nothing this function runs writes to the store.
    """
    rule = restatement_rule()
    threshold = Decimal(str(rule["material_threshold"]))
    identity = tuple(str(column) for column in rule["fact_identity_key"])
    words = vocabulary()
    tables = words["tables"]
    schema = _schema(settings)
    with psycopg.connect(settings["dsn"]) as db, db.cursor() as cur:
        resolved = _resolve_obligor(cur, schema, tables, anchor_lei, fiscal_annual=str(words["fiscal_annual"]), annual_form=str(words["annual_form"]))
        if resolved is None:
            return SpreadRead(anchor_lei=anchor_lei, basis=basis, resolved=None, periods=(), cohort=(), cohort_size=0, cohort_basis=peer_basis)
        cells = _read_cells(cur, schema, tables, anchor_lei, periods=periods, basis=basis, threshold=threshold, identity=identity)
        peers = (
            _read_peers(cur, schema, tables, sic=resolved.sic, period_ends=tuple(sorted({c.period_end for c in cells}, reverse=True)), exclude_cik=resolved.cik)
            if include_peers
            else ()
        )
    if not cells:
        return SpreadRead(anchor_lei=anchor_lei, basis=basis, resolved=None, periods=(), cohort=(), cohort_size=0, cohort_basis=peer_basis)
    return SpreadRead(
        anchor_lei=anchor_lei,
        basis=basis,
        resolved=resolved,
        periods=spread(cells, spreading_convention()),
        cohort=cohort_statistics(peers),
        cohort_size=len({peer.cik for peer in peers}),
        cohort_basis=peer_basis,
    )
