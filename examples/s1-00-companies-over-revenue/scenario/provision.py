"""Hand back a DSN and a seeded database. That is the whole job.

**THIS IS NOT CCF.** [ADAPT] Nothing in this file is a fabric call. It
fabricates the source system the demonstration reads from, so that the example
runs for anyone with Docker and no credential ever enters the tree. An adopter
deletes this file and points the deployment at the database they already run.

Two paths, and the default is the one that needs nothing:

* ``CCF_TEST_POSTGRES_DSN`` set — use it. This is the opt-in path to a real
  server, and it is the same variable ``tests/conftest.py`` gates its Postgres
  leg on, so an operator configures the example and the suite once.
* unset — start a ``postgres:16`` container and use its connection URL.

The resolved DSN is exported under the variable name
``artifacts/config/backends.yaml`` declares, so the connection value reaches the
fabric through the declared ``from_env`` path and is never written down anywhere
— not in an artifact, not in an argument, not in this module.

This mirrors ``tests/conftest.py`` rather than importing it: an example that
imported from the test tree would not stand alone.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg

#: The variable `artifacts/config/backends.yaml` reads the fabric's DSN from.
#: Named here because this module is what sets it; the fabric only ever sees
#: the name, and reads the value out of the environment for itself.
FABRIC_DSN_ENV = "CCF_S1_00_POSTGRES_DSN"

#: The opt-in path to a real server. The suite's own variable, reused.
SUPPLIED_DSN_ENV = "CCF_TEST_POSTGRES_DSN"

SCENARIO = Path(__file__).parent
SCHEMA_SQL = SCENARIO / "schema.sql"
COMPANIES_SQL = SCENARIO / "companies.sql"

#: This deployment's scenario vocabulary — the source table it reads. Not
#: CCF's, and named once here so no other module carries a bare table literal.
TABLE = "companies"


@contextmanager
def provisioned() -> Iterator[str]:
    """Yield a DSN for a seeded Postgres, exported under :data:`FABRIC_DSN_ENV`.

    A context manager because the container path owns a resource it must stop.
    The supplied-DSN path owns nothing and simply yields.
    """
    supplied = os.environ.get(SUPPLIED_DSN_ENV)
    if supplied:
        seed(supplied)
        os.environ[FABRIC_DSN_ENV] = supplied
        yield supplied
        return

    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            f"{SUPPLIED_DSN_ENV} is unset and testcontainers is unavailable"
            f" ({exc}). Either export {SUPPLIED_DSN_ENV} pointing at a Postgres"
            " you already run, or install testcontainers and start Docker."
        ) from exc

    try:
        container = PostgresContainer("postgres:16", driver=None)
        container.start()
    except Exception as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            f"cannot start a Postgres container (is Docker running?) and"
            f" {SUPPLIED_DSN_ENV} is unset. Start Docker, or export"
            f" {SUPPLIED_DSN_ENV} pointing at a Postgres you already run."
        ) from exc
    try:
        dsn = str(container.get_connection_url())
        seed(dsn)
        os.environ[FABRIC_DSN_ENV] = dsn
        yield dsn
    finally:
        container.stop()


def seed(dsn: str) -> int:
    """Apply the schema and the rows, and return how many rows are there.

    Idempotent: the schema is ``if not exists`` and the seed upserts, so a
    repeated run against a long-lived server converges rather than duplicating.
    """
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
            cursor.execute(COMPANIES_SQL.read_text(encoding="utf-8"))
        return row_count(connection)


def row_count(connection: psycopg.Connection[Any]) -> int:
    """How many rows the source table holds."""
    with connection.cursor() as cursor:
        cursor.execute(f"select count(*) from {TABLE}")  # noqa: S608
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    """``--check``: provision, print the seeded row count, and exit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="provision, report the seeded row count, and exit",
    )
    parser.parse_args()
    with provisioned() as dsn:
        with psycopg.connect(dsn) as connection:
            print(f"seeded rows: {row_count(connection)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
