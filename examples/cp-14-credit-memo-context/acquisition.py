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

**One SELECT per question.** The table and column names it uses are read from
``artifacts/source-vocabulary.yaml`` — the roster leg's declared vocabulary — and
nothing here spells one out (CLAUDE.md §6.4).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg import sql

__all__ = ["ResolvedObligor", "resolve", "vocabulary"]

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"


def vocabulary() -> Mapping[str, Any]:
    """The source terms the roster leg reads, named once in an artifact."""
    document: Mapping[str, Any] = yaml.safe_load(
        VOCABULARY.read_text(encoding="utf-8")
    )
    return document["declaration"]


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
    terms = vocabulary()
    tables = terms["tables"]
    key = sql.Identifier(terms["roster_key"])
    columns = sql.SQL(", ").join(
        sql.SQL("e.") + sql.Identifier(column) for column in terms["identity_columns"]
    )
    query = sql.SQL(
        "SELECT {columns}"
        " FROM {s}.{entity} e"
        " WHERE e.{key} = %(lei)s"
        " AND EXISTS (SELECT 1 FROM {s}.{roster} r WHERE r.{key} = e.{key})"
    ).format(
        columns=columns,
        s=sql.Identifier(schema),
        entity=sql.Identifier(tables["legal_entity"]),
        roster=sql.Identifier(tables["memo_context_debt"]),
        key=key,
    )
    with psycopg.connect(settings["dsn"]) as connection, connection.cursor() as cursor:
        cursor.execute(query, {"lei": lei})
        row = cursor.fetchone()
    if row is None:
        return None
    found = dict(zip(terms["identity_columns"], row, strict=True))
    return ResolvedObligor(
        lei=str(found["lei"]),
        legal_name=str(found["legal_name"] or ""),
        legal_jurisdiction=str(found["legal_jurisdiction"] or ""),
        sic=str(found["sic"] or ""),
        sic_description=str(found["sic_description"] or ""),
        retrieved_at=found["retrieved_at"],
    )
