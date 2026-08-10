"""Deterministic materialiser for the KYC/UBO enterprise source estate.

**What it is.** A pure interpreter of ``artifacts/source-estate.yaml``
(CLAUDE.md §6.4, the No-Hardcoding Rule; phase 16 CONTEXT D-03). Given the
declared estate it writes standalone *source-system* files — JSONL documents
in the shipped FIBO shape, and a SQLite database in the shape
``load_postgres.py`` builds, with one added observation-time column that L1
ingress reads.

**It holds no vocabulary.** No entity name, no relationship type string, no
percentage, no jurisdiction, no date, no threshold. Everything domain-specific
comes from the artifact; this module knows only mechanism roles — the
declaration keys named in the constants below, the two output formats, and the
one column role. An estate for a different domain is a different artifact and
the same module. Deleting the artifact leaves this file with nothing to do,
which is the property CLAUDE.md §6.4 is after.

**Single-writer (CLAUDE.md §10; phase 16 CONTEXT D-04).** This module never
touches CCF's Context Graph. It writes an *enterprise source estate* — the
world that exists before any fabric does — and nothing it produces enters L3
except through L2 ingress in a later plan. This is D-04's read-side/write-side
split expressed as code: CCF *reads* an enterprise estate at L1 and assembles
selectively; it never mirrors the estate wholesale into its own graph. The
module imports nothing under ``ccf.graph``, ``ccf.boot`` or ``ccf.deployment``,
and ``tests/examples/test_source_estate.py`` states that as an AST check rather
than as a comment.

**Determinism.** One ``random.Random(seed + rng_offset)`` per stream, with the
offset declared per stream in the artifact rather than implied by ordering, so
a stream added later cannot silently renumber another's. Every timestamp
derives from the artifact's fixed ``epoch`` plus a per-record interval and a
seeded jitter — never a clock read. The same inputs produce byte-identical
output, which is what lets plan 16-07's backend matrix compare a content hash
across substrates. Checksums hash sorted logical row content, never file bytes.

**Emission order is the declared order.** The estate is fully declared, so the
seed drives observation times rather than row order. Keeping declared order
means each measured FIBO record comes back verbatim, which is what makes the
"is the extension additive?" check at the human checkpoint a readable diff.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any, cast

import yaml

from ccf.controlplane.artifacts import (
    ArtifactLoadError,
    DeclaredArtifact,
    declared_artifact_class,
    load_artifact,
)

__all__ = [
    "ARTIFACT_PATH",
    "SourceEstateError",
    "generate",
    "load_declaration",
    "sql_identifier",
    "stream_checksum",
]

#: The declared estate this module interprets, beside the module itself.
ARTIFACT_PATH = (
    pathlib.Path(__file__).resolve().parent / "artifacts" / "source-estate.yaml"
)

# --- mechanism keys the interpreter understands ----------------------------
# Every one of these is structural. None of them is a domain value.

KEY_CLASS_ID = "class_id"
KEY_SEED = "seed"
KEY_EPOCH = "epoch"
KEY_STREAMS = "streams"
KEY_RNG_OFFSET = "rng_offset"
KEY_INTERVAL = "observation_interval_seconds"
KEY_JITTER = "observation_jitter_seconds"
KEY_RECORDS = "records"
KEY_OUTPUTS = "outputs"
KEY_FORMAT = "format"
KEY_PATH = "path"
KEY_STREAM = "stream"
KEY_TABLES = "tables"
KEY_NAME = "name"
KEY_COLUMNS = "columns"
KEY_FIELD = "field"
KEY_ENCODE = "encode"
KEY_ROLE = "role"

FORMAT_JSONL = "jsonl"
FORMAT_SQLITE = "sqlite"
ENCODE_JSON = "json"
ROLE_OBSERVATION_TIME = "observation_time"


class SourceEstateError(RuntimeError):
    """The declared estate is missing, unreadable, or structurally incomplete.

    Raised rather than defaulted. A generator that invents a default when its
    artifact is absent is a generator that has the vocabulary in it after all.
    """


def sql_identifier(name: object) -> str:
    """Quote an artifact-supplied SQL identifier, escaping embedded quotes.

    Table and column names cannot travel as bound parameters; they come from
    the versioned artifact and are double-quoted here with any embedded ``"``
    doubled, so a hostile identifier cannot break out of the quoting. Values
    always travel as bound parameters. Mechanism only (CLAUDE.md §6.4).
    """
    return '"' + str(name).replace('"', '""') + '"'


def _require(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise SourceEstateError(
            f"{where}: the declared estate names no `{key}`;"
            f" see `{ARTIFACT_PATH.name}`"
        )
    return mapping[key]


def load_declaration(path: pathlib.Path | None = None) -> Mapping[str, Any]:
    """Read the declared estate, validated by the SDK's own artifact loader.

    The class id comes out of the *document* rather than out of this module —
    naming it here would be putting the deployment's vocabulary back into the
    code. The envelope contract is what refuses a YAML float or a zone-less
    timestamp, so the estate is held to the same admissibility rules every
    other Control Plane artifact is.

    Raises:
        SourceEstateError: the artifact is absent, is not a mapping, declares
            no class, or is refused by its own contract.
    """
    source = ARTIFACT_PATH if path is None else pathlib.Path(path)
    if not source.is_file():
        raise SourceEstateError(
            f"no declared estate at {source} — this module is an interpreter"
            " and has nothing to interpret without its artifact"
            " (CLAUDE.md §6.4)"
        )
    text = source.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    if not isinstance(document, Mapping):
        raise SourceEstateError(f"{source}: not a YAML mapping")
    class_id = document.get(KEY_CLASS_ID)
    if not isinstance(class_id, str):
        raise SourceEstateError(
            f"{source}: declares no `{KEY_CLASS_ID}`, so nothing states which"
            " artifact class it is"
        )
    try:
        artifact = load_artifact(text, declared_artifact_class(class_id))
    except ArtifactLoadError as rejected:
        raise SourceEstateError(f"{source}: {rejected}") from rejected
    return cast(DeclaredArtifact, artifact).declaration


def _materialise_stream(
    name: str, spec: Mapping[str, Any], seed: int, epoch: datetime
) -> list[tuple[Mapping[str, Any], str]]:
    """Pair every declared record with its derived observation time."""
    where = f"{KEY_STREAMS}.{name}"
    records = _require(spec, KEY_RECORDS, where)
    if not isinstance(records, Sequence) or not records:
        raise SourceEstateError(f"{where}.{KEY_RECORDS}: no records declared")
    rng = random.Random(seed + int(_require(spec, KEY_RNG_OFFSET, where)))
    interval = int(_require(spec, KEY_INTERVAL, where))
    jitter = int(_require(spec, KEY_JITTER, where))
    materialised: list[tuple[Mapping[str, Any], str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise SourceEstateError(f"{where}.{KEY_RECORDS}[{index}]: not a mapping")
        observed = epoch + timedelta(
            seconds=index * interval + rng.randrange(jitter + 1)
        )
        materialised.append((record, observed.isoformat()))
    return materialised


def stream_checksum(rows: Sequence[tuple[Mapping[str, Any], str]]) -> str:
    """Hash a stream's SORTED logical content — never file bytes.

    File bytes carry incidental structure (page layout, insertion order) that
    says nothing about whether the estate is the same estate. Sorting the
    canonical JSON of each row makes this a statement about content.
    """
    digest = hashlib.sha256()
    for line in sorted(
        json.dumps(
            {**record, ROLE_OBSERVATION_TIME: observed},
            sort_keys=True,
            ensure_ascii=True,
        )
        for record, observed in rows
    ):
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _write_jsonl(
    destination: pathlib.Path, rows: Sequence[tuple[Mapping[str, Any], str]]
) -> None:
    """Emit the declared records verbatim, one JSON document per line.

    No derived field is added here. The JSONL documents are what the four
    out-of-tree loaders read, and a field this module invented would break the
    "the extension is a superset of the shipped dataset" property the human
    checkpoint verifies by eye.
    """
    destination.write_text(
        "".join(f"{json.dumps(dict(record))}\n" for record, _ in rows),
        encoding="utf-8",
    )


def _column_value(
    column: Mapping[str, Any], record: Mapping[str, Any], observed: str
) -> Any:
    if column.get(KEY_ROLE) == ROLE_OBSERVATION_TIME:
        return observed
    value = record.get(_require(column, KEY_FIELD, KEY_COLUMNS))
    if value is None:
        return None
    if column.get(KEY_ENCODE) == ENCODE_JSON:
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    return value


def _write_sqlite(
    destination: pathlib.Path,
    tables: Sequence[Mapping[str, Any]],
    streams: Mapping[str, list[tuple[Mapping[str, Any], str]]],
) -> None:
    """Build the declared tables and insert the declared rows.

    Identifiers are artifact-supplied and quoted; every value travels as a
    bound parameter.
    """
    destination.unlink(missing_ok=True)
    connection = sqlite3.connect(destination)
    try:
        for table in tables:
            where = f"{KEY_OUTPUTS}.{KEY_TABLES}"
            stream_name = _require(table, KEY_STREAM, where)
            if stream_name not in streams:
                raise SourceEstateError(
                    f"{where}: names stream {stream_name!r}, which is not"
                    f" declared under `{KEY_STREAMS}`"
                )
            columns = _require(table, KEY_COLUMNS, where)
            names = [_require(column, KEY_NAME, where) for column in columns]
            table_sql = sql_identifier(_require(table, KEY_NAME, where))
            column_sql = ", ".join(f"{sql_identifier(name)} TEXT" for name in names)
            connection.execute(f"CREATE TABLE {table_sql} ({column_sql})")
            placeholders = ", ".join("?" for _ in names)
            insert_sql = (
                f"INSERT INTO {table_sql}"
                f" ({', '.join(sql_identifier(name) for name in names)})"
                f" VALUES ({placeholders})"
            )
            connection.executemany(
                insert_sql,
                [
                    tuple(
                        _column_value(column, record, observed)
                        for column in columns
                    )
                    for record, observed in streams[stream_name]
                ],
            )
        connection.commit()
    finally:
        connection.close()


def generate(
    declaration: Mapping[str, Any], output_dir: pathlib.Path
) -> dict[str, Any]:
    """Materialise the declared estate under ``output_dir``.

    Returns a manifest: the files written, the row count per stream, and the
    logical checksum per stream. Nothing here reaches CCF's Context Graph.
    """
    if not isinstance(declaration, Mapping) or not declaration:
        raise SourceEstateError(
            "no declared estate supplied; call `load_declaration()` first"
        )
    root = pathlib.Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    where = "declaration"
    seed = int(_require(declaration, KEY_SEED, where))
    epoch = datetime.fromisoformat(str(_require(declaration, KEY_EPOCH, where)))
    stream_specs = _require(declaration, KEY_STREAMS, where)
    streams = {
        name: _materialise_stream(name, spec, seed, epoch)
        for name, spec in stream_specs.items()
    }

    written: list[str] = []
    for index, output in enumerate(_require(declaration, KEY_OUTPUTS, where)):
        origin = f"{KEY_OUTPUTS}[{index}]"
        destination = root / str(_require(output, KEY_PATH, origin))
        kind = _require(output, KEY_FORMAT, origin)
        if kind == FORMAT_JSONL:
            name = _require(output, KEY_STREAM, origin)
            if name not in streams:
                raise SourceEstateError(
                    f"{origin}: names stream {name!r}, which is not declared"
                    f" under `{KEY_STREAMS}`"
                )
            _write_jsonl(destination, streams[name])
        elif kind == FORMAT_SQLITE:
            _write_sqlite(destination, _require(output, KEY_TABLES, origin), streams)
        else:
            raise SourceEstateError(f"{origin}: unknown `{KEY_FORMAT}` {kind!r}")
        written.append(destination.name)

    return {
        "output_dir": root,
        "files": written,
        "counts": {name: len(rows) for name, rows in streams.items()},
        "checksums": {
            name: stream_checksum(rows) for name, rows in streams.items()
        },
    }
