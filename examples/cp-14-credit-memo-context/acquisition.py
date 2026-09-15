"""The parent's OWN source leg in this slice: the memo roster, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**: somebody else's store, read the way that store wants to be read.

**What this slice reads, and why only this.** The memo roster is the twenty
obligors of `memo_context_debt` joined to their `legal_entity` records (spec
§C.1). The obligor's IDENTITY — name, jurisdiction, SIC — is the parent's own
evidence; its membership on the roster is what admits the question. **No
figure is read from `memo_context_debt`**: that table is a dated diagnostic
(`as_of` 2026-08-22) and never the governing source (`CMC-G04`); the join is an
existence test. Everything a memo prints about the obligor's finances, family,
exposure, collateral and covenants is a CHILD'S, acquired through the composite
and never rebuilt here (`CMC-G27`, spec §B.8).

**One SELECT per question.**
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import psycopg
from psycopg import sql

__all__ = ["ResolvedObligor", "resolve"]


@dataclass(frozen=True)
class ResolvedObligor:
    """The obligor's identity record, as the estate holds it."""

    lei: str
    legal_name: str
    legal_jurisdiction: str
    sic: str
    sic_description: str
    retrieved_at: date | None


def _schema(settings: Mapping[str, str]) -> str:
    schema = settings["schema"]
    if not schema.replace("_", "").isalnum():
        raise ValueError(f"schema name {schema!r} is not an identifier")
    return schema


def resolve(lei: str, *, settings: Mapping[str, str]) -> ResolvedObligor | None:
    """The roster member ``lei`` names, or ``None`` when the LEI is not on the roster.

    An LEI with an identity record but no roster row resolves to nothing: the
    memo roster, not the entity universe, is this product's population.
    """
    schema = _schema(settings)
    query = sql.SQL(
        "SELECT e.lei, e.legal_name, e.legal_jurisdiction, e.sic, e.sic_description, e.retrieved_at"
        " FROM {s}.legal_entity e"
        " WHERE e.lei = %(lei)s"
        " AND EXISTS (SELECT 1 FROM {s}.memo_context_debt r WHERE r.lei = e.lei)"
    ).format(s=sql.Identifier(schema))
    with psycopg.connect(settings["dsn"]) as connection, connection.cursor() as cursor:
        cursor.execute(query, {"lei": lei})
        row = cursor.fetchone()
    if row is None:
        return None
    return ResolvedObligor(
        lei=str(row[0]),
        legal_name=str(row[1] or ""),
        legal_jurisdiction=str(row[2] or ""),
        sic=str(row[3] or ""),
        sic_description=str(row[4] or ""),
        retrieved_at=row[5],
    )
