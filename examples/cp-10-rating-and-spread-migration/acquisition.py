"""The two source reads, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing.

Opens PostgreSQL and Fluree, reads, hands back typed rows. No fabric call, no
gate, no serve, and **no clock**: every instant arrives as an argument, because
a module that read one would make the product's own decision instant
unreproducible (`D-IMPL-98`).

**Reads only.** The ledger is append-only, so a write is permanent, and nothing
here writes to either store (`CP-SPEC-010` §0.3).

## What this module does NOT read, and it is checked rather than assumed

**No agency ratings and no TRACE** (`CP-SPEC-010` §0.4). There is no agency
column in this estate and no TRACE table; the grade history is the internal
one, and the spread is a decomposition of two public series plus an engineered
residual. Neither absence is worked around and neither is described as
something else.

## The decomposition this module hands back, unsummed

    yield_bp = benchmark_bp + market_oas_bp + idiosyncratic_bp
               └─ public ─┘  └─ public ──┘   └── the signal ──┘

The three components travel **separately** all the way to the payload. Summing
them here would destroy the product's subject in its first function
(`RSM-G07`), and the market component is what makes `idiosyncratic_bp` evidence
about *this obligor* rather than about its whole rating band.
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


def vocabulary() -> Mapping[str, Any]:
    """The source's own IRIs, from the artifact rather than spelled in code."""
    document = yaml.safe_load(
        (HERE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    )
    declaration: Mapping[str, Any] = document["declaration"]
    return declaration


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. This example reads a live estate; see the"
            " README's Run-it section for the read-only role it needs"
        )
    return value


@dataclass(frozen=True)
class Obligor:
    lei: str
    label: str


@dataclass(frozen=True)
class Instrument:
    """One debt instrument, and **the band its market leg is netted on**.

    `issue_band` is `CP-SPEC-010`'s `static_issue_band` basis: the band the
    instrument was issued into. It does NOT migrate with the obligor's grade,
    and the product must not infer a replacement from that grade — a residual
    computed from a grade-derived band could not disagree with the grade, which
    is the whole subject of this rung (`CP10-F-04`, `RSM-G23`).
    """

    instrument_id: str
    issue_band: str
    coupon_pct: Decimal
    maturity: date
    seniority: str
    tenor_years: int


@dataclass(frozen=True)
class SpreadPoint:
    """One day's decomposition for one instrument. The three parts stay apart."""

    instrument_id: str
    obs_date: date
    benchmark_bp: Decimal
    market_oas_bp: Decimal
    idiosyncratic_bp: Decimal
    yield_bp: Decimal


@dataclass(frozen=True)
class Grade:
    """One internal grade assertion, on **both** of its clocks.

    `valid_from` is when the grade took effect; `asserted_at` is when it was
    booked. Measured on the anchor: a four-day lag. Both are served and they
    are not the same claim (`RSM-G13`).
    """

    grade: str
    valid_from: date
    valid_to: date | None
    asserted_at: date
    trigger: str
    superseded_by: str | None

    @property
    def off_cycle(self) -> bool:
        """Whether this assertion came from something other than the cycle.

        Read off the trigger text rather than inferred from spacing: a review
        that happens to fall near a spread peak is not an off-cycle review, and
        confusing the two is `TRAP 2` (`CP-SPEC-010` §C.4).
        """
        return self.trigger not in ("quarterly review", "initial rating (window start)")


@dataclass(frozen=True)
class Estate:
    obligor: Obligor
    instruments: tuple[Instrument, ...]
    spreads: tuple[SpreadPoint, ...]
    grades: tuple[Grade, ...]
    scale: Mapping[str, int]
    #: Grade -> the rating BAND it sits in, read from the scale artifact.
    #: Used to report whether an obligor has migrated out of the band its
    #: instruments were issued into — NEVER to re-derive the market leg's
    #: band, which would make the market a function of the grade
    #: (`CP10-F-04`, `RSM-G23`).
    bands: Mapping[str, str]
    scale_version: str
    window_from: date
    window_to: date


class UnknownObligor(LookupError):
    """The anchor resolves to no obligor.

    Raised rather than returning an empty series: an unknown obligor is a claim
    about the REQUEST; an obligor with no traded debt is a claim about the
    world. They mean opposite things (`RSM-G17`).
    """


class _Relational:
    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with psycopg.connect(self._dsn) as connection:
            cursor = connection.cursor()
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            return list(cursor.fetchall())


class _Graph:
    """The ledger over SPARQL. No transaction pin.

    The grade history is versioned by `validFrom` IN THE DATA, so the answer is
    a function of the decision instant rather than of the store's `t`. A pin
    would say which store state answered, which this product does not claim.
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


def _cell(row: Mapping[str, Any], name: str) -> str | None:
    value = row.get(name)
    return None if value is None else str(value.get("value"))


def acquire(*, anchor_lei: str, asked_at: datetime, window_days: int) -> Estate:
    """Read both legs for one obligor over one window ending at `asked_at`.

    The window's right edge is the decision instant and its left edge is
    `window_days` before. Nothing later than `asked_at` is read on either leg —
    a grade effective after the decision instant is not yet in force, and a
    spread observed after it is not yet knowable (`RSM-G10`).
    """
    relational = _Relational(
        dsn=_setting("CCF_CP_10_POSTGRES_DSN"),
        schema=_setting("CCF_CP_10_POSTGRES_SCHEMA"),
    )
    graph = _Graph(
        url=_setting("CCF_CP_10_FLUREE_URL"),
        ledger=_setting("CCF_CP_10_FLUREE_LEDGER"),
    )
    terms = vocabulary()
    window_to = asked_at.date()
    window_from = date.fromordinal(window_to.toordinal() - window_days)

    found = relational.rows(
        "SELECT lei, legal_name FROM legal_entity WHERE lei = %s", (anchor_lei,)
    )
    if not found:
        raise UnknownObligor(
            f"obligor {anchor_lei!r} is not available (404); this product serves"
            " obligors the estate holds and fails closed rather than returning"
            " an empty migration series"
        )
    obligor = Obligor(lei=str(found[0][0]).strip(), label=str(found[0][1]))

    instruments = tuple(
        Instrument(
            instrument_id=str(r[0]), issue_band=str(r[1]), coupon_pct=r[2],
            maturity=r[3], seniority=str(r[4]), tenor_years=int(r[5]),
        )
        for r in relational.rows(
            "SELECT instrument_id, rating_band, coupon_pct, maturity, seniority,"
            " tenor_years FROM debt_instrument WHERE lei = %s"
            " ORDER BY instrument_id",
            (anchor_lei,),
        )
    )

    spreads: tuple[SpreadPoint, ...] = ()
    if instruments:
        spreads = tuple(
            SpreadPoint(
                instrument_id=str(r[0]), obs_date=r[1], benchmark_bp=r[2],
                market_oas_bp=r[3], idiosyncratic_bp=r[4], yield_bp=r[5],
            )
            for r in relational.rows(
                "SELECT instrument_id, obs_date, benchmark_bp, market_oas_bp,"
                " idiosyncratic_bp, yield_bp FROM spread_observation"
                " WHERE instrument_id = ANY(%s) AND obs_date BETWEEN %s AND %s"
                " ORDER BY instrument_id, obs_date",
                ([i.instrument_id for i in instruments], window_from, window_to),
            )
        )

    scale_rows = relational.rows(
        "SELECT grade, notch, policy_version, rating_band FROM rating_scale"
        " ORDER BY notch"
    )
    scale = {str(r[0]): int(r[1]) for r in scale_rows}
    # The BAND each notch belongs to, from the scale itself rather than by
    # stripping the modifier off the letter in code — the mapping is policy,
    # and a deployment that reshaped its scale would want this to follow.
    bands = {str(r[0]): str(r[3]) for r in scale_rows}
    scale_version = str(scale_rows[0][2]) if scale_rows else "unversioned"

    return Estate(
        obligor=obligor, instruments=instruments, spreads=spreads,
        grades=grade_history(
            graph, terms, lei=anchor_lei, window_from=window_from, window_to=window_to
        ),
        scale=scale, bands=bands, scale_version=scale_version,
        window_from=window_from, window_to=window_to,
    )


def grade_history(
    graph: _Graph, terms: Mapping[str, Any], *, lei: str,
    window_from: date, window_to: date,
) -> tuple[Grade, ...]:
    """Every internal grade assertion in force at or during the window.

    **Bounded at the decision instant on the EFFECTIVE axis.** An assertion
    whose `validFrom` is after `window_to` has not taken effect yet and is not
    read — so an earlier `as_of` genuinely omits a later downgrade rather than
    flagging it differently (`RSM-G10`, §D.6 step 3).

    The booking axis is carried but does NOT bound the read: rung 8 owns
    reconstruction on assertion time, and answering that question here would be
    two products answering one question differently (`CP-SPEC-010` §B.6).
    """
    rows = graph.select(
        f"SELECT ?g ?vf ?vt ?aa ?tr ?sb FROM <{graph.dataset}> WHERE {{"
        f" ?s a <{terms['rating_class']}> ;"
        f" <{terms['concerns_party']}> ?party ;"
        f" <{terms['grade']}> ?g ;"
        f" <{terms['valid_from']}> ?vf ;"
        f" <{terms['asserted_at']}> ?aa ;"
        f" <{terms['trigger']}> ?tr ."
        f" OPTIONAL {{ ?s <{terms['valid_to']}> ?vt }}"
        f" OPTIONAL {{ ?s <{terms['superseded_by']}> ?sb }}"
        f' ?party <{terms["lei"]}> "{lei}" }}'
    )
    admitted: list[Grade] = []
    for row in rows:
        valid_from = date.fromisoformat(str(_cell(row, "vf")))
        if valid_from > window_to:
            continue
        valid_to_raw = _cell(row, "vt")
        valid_to = date.fromisoformat(valid_to_raw) if valid_to_raw else None
        # In force at some point inside the window, or the one still in force
        # when the window opened. An assertion that closed before the window
        # began is not part of this migration.
        if valid_to is not None and valid_to < window_from:
            continue
        superseded = _cell(row, "sb")
        admitted.append(
            Grade(
                grade=str(_cell(row, "g")), valid_from=valid_from, valid_to=valid_to,
                asserted_at=date.fromisoformat(str(_cell(row, "aa"))),
                trigger=str(_cell(row, "tr")),
                superseded_by=superseded.rsplit("/", 1)[-1] if superseded else None,
            )
        )
    return tuple(sorted(admitted, key=lambda g: g.valid_from))
