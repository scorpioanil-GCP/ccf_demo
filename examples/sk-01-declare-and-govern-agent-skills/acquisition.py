# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The parent's OWN source leg: the obligor's identity row, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**: somebody else's store, read the way that store wants to be read.

**Why this leg exists.** It is not what this example is about. A product on the
paved road must have an own leg — an empty own view refuses — and on today's
SDK the agent whose skills this example governs lives only inside a product
(SK01-F-05 in FINDINGS.md). So the brief reads one row: the obligor's identity.
Everything it says about collateral and set-off is the CHILD's, acquired through
the composite and never read here.

**One SELECT per question.** The table, the key and the SELECT column list are
read from ``artifacts/source-vocabulary.yaml``. The four result names are
restated in :func:`resolve`, which indexes the row by them, so a column renamed
in the vocabulary needs the matching change here — it fails loudly, a
``KeyError`` — and the same attribute names are stated three more times
(``ccf_config.yaml``'s ``resolution``, ``deployment.py``'s payload keys and
``projection.py``'s obligor block). That duplication is recorded as friction in
FINDINGS.md (§E, "duplicated configuration authorities").

**A null is passed through, never coerced.** A column the estate holds as null
comes back as ``None``; the SDK omits a null attribute from the fabric
(`D-IMPL-357` B4), and Π prints the declared ``not_evaluable`` word for it
rather than an empty string.
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
    """The source terms the identity leg reads, named once in an artifact."""
    document: Mapping[str, Any] = yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))
    return document["declaration"]


@dataclass(frozen=True)
class ResolvedObligor:
    """The obligor's identity record, as the estate holds it."""

    lei: str
    legal_name: str | None
    legal_jurisdiction: str | None
    retrieved_at: date | None


def _schema(settings: Mapping[str, str]) -> str:
    schema = settings["schema"]
    if not schema.replace("_", "").isalnum():
        raise ValueError(f"schema name {schema!r} is not an identifier")
    return schema


def resolve(lei: str, *, settings: Mapping[str, str]) -> ResolvedObligor | None:
    """The identity record ``lei`` names, or ``None`` when the estate holds none."""
    terms = vocabulary()
    columns = list(terms["identity_columns"])
    query = sql.SQL("SELECT {columns} FROM {schema}.{table} WHERE {key} = %(lei)s").format(
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        schema=sql.Identifier(_schema(settings)),
        table=sql.Identifier(terms["table"]),
        key=sql.Identifier(terms["key"]),
    )
    with psycopg.connect(settings["dsn"]) as connection, connection.cursor() as cursor:
        cursor.execute(query, {"lei": lei})
        row = cursor.fetchone()
    if row is None:
        return None
    found = dict(zip(columns, row, strict=True))
    # The four result names, restated (see the module docstring and FINDINGS.md §E).
    return ResolvedObligor(
        lei=str(found["lei"]),
        legal_name=None if found["legal_name"] is None else str(found["legal_name"]),
        legal_jurisdiction=None if found["legal_jurisdiction"] is None else str(found["legal_jurisdiction"]),
        retrieved_at=found["retrieved_at"],
    )
