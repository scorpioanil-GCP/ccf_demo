"""Deterministic synthetic source-system generator for the e2e demo (DEMO-01).

This module is a **pure interpreter** of ``artifacts/scenario.yaml``
(CLAUDE.md §6.4 No-Hardcoding Rule; Phase 12 CONTEXT D-05..D-08): it holds no
vocabulary — no source names, table names, column names, aliases, amounts, or
lexicon words. Everything domain-specific comes from the scenario artifact;
this code knows only mechanism roles (``ledger``, ``transfer_log``,
``registry``; ``entities``/``movements`` tables; per-column role keys).

Structural constraints:

- **Single-writer (CLAUDE.md §10):** this module never touches the Context
  Graph. It writes standalone SQLite *source-system* files only; rows enter
  the fabric exclusively through ``handle.worker.ingest`` in ``run.py``.
- **Determinism (D-08, mirroring perf/synth's discipline — never its
  ontology, D-05):** one ``random.Random(scenario["seed"] + offset)`` per
  generation stream with the documented offsets below; every timestamp
  derives from the scenario's fixed ``epoch`` plus offsets — never a clock
  read — and is stored as ISO-8601 text with an explicit ``+00:00`` offset
  (RESEARCH Pitfall 1). Checksums hash SORTED logical row content, never
  file bytes (RESEARCH Pitfall 2).
- **Parameterized SQL only** (threat register T-12-01): table/column names
  come from the versioned artifact and are quoted; values always travel as
  bound parameters.

Seeded stream offsets (documented, D-08):

====== =========================================================
offset stream
====== =========================================================
0      noise counterparty population (names, tax ids, addresses)
1      ledger noise (entity ids, balances, movement rows)
2      transfer-log noise (wire references, parties, amounts)
3      registry noise (registry ids, registration dates)
4      per-table row interleaving (ring rows shuffled into noise)
====== =========================================================
"""

from __future__ import annotations

import hashlib
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

__all__ = ["generate", "source_checksum"]

# Documented RNG stream offsets (see module docstring).
_STREAM_POPULATION = 0
_STREAM_LEDGER = 1
_STREAM_TRANSFERS = 2
_STREAM_REGISTRY = 3
_STREAM_INTERLEAVE = 4


# ---------------------------------------------------------------------------
# Checksums — logical content, never file bytes (RESEARCH Pitfall 2).
# ---------------------------------------------------------------------------


def source_checksum(db_path: Path, table: str, columns: list[str]) -> str:
    """sha256 over the SORTED logical row tuples of one table.

    Rows are read with an ``ORDER BY`` over every listed column and hashed as
    sorted ``|``-joined text lines, so neither insertion order nor SQLite
    file-format details can leak into the pin (D-08).
    """
    quoted = ", ".join(f'"{c}"' for c in columns)
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            f'SELECT {quoted} FROM "{table}" ORDER BY {quoted}'
        ).fetchall()
    digest = hashlib.sha256()
    for line in sorted("|".join(str(v) for v in row) for row in rows):
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _combined_source_checksum(db_path: Path, tables: dict[str, Any]) -> str:
    """One checksum per source: sha256 over its sorted per-table checksums."""
    digest = hashlib.sha256()
    for table in sorted(t["name"] for t in tables.values()):
        spec = next(t for t in tables.values() if t["name"] == table)
        names = [c["name"] for c in spec["columns"]]
        digest.update(f"{table}:{source_checksum(db_path, table, names)}\n".encode())
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Small deterministic helpers — all vocabulary arrives as arguments.
# ---------------------------------------------------------------------------


def _epoch(scenario: dict[str, Any]) -> datetime:
    stamp = datetime.fromisoformat(str(scenario["epoch"]))
    if stamp.tzinfo is None:
        raise ValueError("scenario epoch must carry an explicit UTC offset")
    return stamp


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _amount(rng: random.Random, bounds: dict[str, Any]) -> str:
    low, high = float(bounds["min"]), float(bounds["max"])
    if not low < high:
        raise ValueError(f"infeasible amount bounds: {bounds!r}")
    return f"{rng.uniform(low, high):.2f}"


def _digits(rng: random.Random, count: int) -> str:
    return "".join(str(rng.randrange(10)) for _ in range(count))


def _row(table: dict[str, Any], values: dict[str, Any]) -> tuple[Any, ...]:
    """Order role-keyed values into the artifact's declared column order."""
    missing = {c["role"] for c in table["columns"]} - set(values)
    if missing:
        raise ValueError(f"row is missing roles {sorted(missing)}")
    return tuple(values[c["role"]] for c in table["columns"])


def _create_and_fill(
    db_path: Path,
    table: dict[str, Any],
    rows: list[tuple[Any, ...]],
) -> None:
    columns_sql = ", ".join(f'"{c["name"]}" {c["type"]}' for c in table["columns"])
    placeholders = ", ".join("?" for _ in table["columns"])
    with sqlite3.connect(db_path) as connection:
        connection.execute(f'CREATE TABLE "{table["name"]}" ({columns_sql})')
        connection.executemany(
            f'INSERT INTO "{table["name"]}" VALUES ({placeholders})', rows
        )
        connection.commit()


def _source_by_role(scenario: dict[str, Any], role: str) -> tuple[str, dict[str, Any]]:
    for name, source in scenario["sources"].items():
        if source["role"] == role:
            return name, source
    raise ValueError(f"scenario declares no source with role {role!r}")


# ---------------------------------------------------------------------------
# Noise population — one seeded pass, shared by all three sources.
# ---------------------------------------------------------------------------


def _population(scenario: dict[str, Any]) -> list[dict[str, str]]:
    """The deterministic noise-counterparty population (stream offset 0)."""
    noise = scenario["noise"]
    rng = random.Random(int(scenario["seed"]) + _STREAM_POPULATION)
    prefixes = noise["id_prefixes"]
    population: list[dict[str, str]] = []
    for index in range(int(noise["counts"]["population"])):
        name = " ".join(
            (
                rng.choice(noise["company_words"]),
                rng.choice(noise["company_activities"]),
                rng.choice(noise["company_suffixes"]),
            )
        )
        population.append(
            {
                "name": name,
                "tax_id": f"{prefixes['tax']}-{_digits(rng, 2)}-{_digits(rng, 7)}",
                "address": (
                    f"{rng.randrange(1, 250)} {rng.choice(noise['streets'])}, "
                    f"{rng.choice(noise['cities'])}"
                ),
                "jurisdiction": rng.choice(noise["jurisdictions"]),
                "registry_id": f"{prefixes['registry']}-{10000 + index}",
            }
        )
    return population


# ---------------------------------------------------------------------------
# Public surface.
# ---------------------------------------------------------------------------


def generate(scenario: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    """Write the three SQLite source-system files and return the shape.

    Returns ``{"row_counts": .., "checksums": .., "ring_signature": ..}``
    keyed by the scenario's own source and table names, so the caller (and
    the determinism test) can compare directly against the artifact's
    ``expected`` block.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(scenario["seed"])
    epoch = _epoch(scenario)
    noise = scenario["noise"]
    counts = noise["counts"]
    members = {m["key"]: m for m in scenario["ring"]["members"]}
    population = _population(scenario)

    account_target = int(counts["ledger_entities"])
    if account_target > len(population):
        raise ValueError(
            f"ledger_entities={account_target} exceeds the "
            f"{len(population)}-counterparty population"
        )

    interleave = random.Random(seed + _STREAM_INTERLEAVE)
    row_counts: dict[str, dict[str, int]] = {}
    checksums: dict[str, str] = {}

    def emit(source: dict[str, Any], name: str, tables_rows: dict[str, list[tuple[Any, ...]]]) -> None:
        db_path = out_dir / source["db_file"]
        db_path.unlink(missing_ok=True)
        row_counts[name] = {}
        for table_role, rows in tables_rows.items():
            table = source["tables"][table_role]
            interleave.shuffle(rows)  # ring rows hide among the noise
            _create_and_fill(db_path, table, rows)
            row_counts[name][table["name"]] = len(rows)
        checksums[name] = _combined_source_checksum(db_path, source["tables"])

    # --- ledger source: entity and movement rows ---------------------------
    ledger_name, ledger = _source_by_role(scenario, "ledger")
    rng = random.Random(seed + _STREAM_LEDGER)
    prefixes = noise["id_prefixes"]
    history_days = int(noise["time"]["history_days"])
    activity_days = int(noise["time"]["activity_days"])
    if history_days <= 30 or activity_days <= 0:
        raise ValueError(f"infeasible time bounds: {noise['time']!r}")

    accounts: list[tuple[Any, ...]] = []
    account_numbers: list[str] = []
    entities_table = ledger["tables"]["entities"]
    for person in population[:account_target]:
        number = (
            f"{prefixes['account']}-{_digits(rng, 2)}-"
            f"{_digits(rng, 4)}-{_digits(rng, 4)}"
        )
        account_numbers.append(number)
        accounts.append(
            _row(
                entities_table,
                {
                    "id": number,
                    "holder": person["name"],
                    "tax_id": person["tax_id"],
                    "currency": rng.choice(noise["currencies"]),
                    "balance": _amount(rng, noise["amounts"]["balance"]),
                    "opened": _iso(
                        epoch - timedelta(days=rng.randrange(30, history_days))
                    ),
                },
            )
        )
    for member in members.values():
        spec = member["ledger"]
        account_numbers.append(spec["id"])
        accounts.append(
            _row(
                entities_table,
                {
                    "id": spec["id"],
                    "holder": spec["holder"],
                    "tax_id": spec["tax_id"],
                    "currency": spec["currency"],
                    "balance": spec["balance"],
                    "opened": _iso(
                        epoch + timedelta(days=int(spec["opened_day_offset"]))
                    ),
                },
            )
        )

    movements_table = ledger["tables"]["movements"]
    transactions: list[tuple[Any, ...]] = []
    for index in range(int(counts["ledger_movements"])):
        debit = rng.choice(account_numbers)
        credit = rng.choice(account_numbers)
        transactions.append(
            _row(
                movements_table,
                {
                    "id": f"{prefixes['transaction']}-{100000 + index}",
                    "account": debit,
                    "counterparty_account": credit,
                    "amount": _amount(rng, noise["amounts"]["transaction"]),
                    "currency": rng.choice(noise["currencies"]),
                    "booked": _iso(
                        epoch
                        + timedelta(
                            days=rng.randrange(activity_days),
                            minutes=rng.randrange(1440),
                        )
                    ),
                    "memo": rng.choice(noise["memos"]),
                },
            )
        )
    emit(ledger, ledger_name, {"entities": accounts, "movements": transactions})

    # --- transfer-log source: noise wires + the planted ring edges --------
    transfers_name, transfers = _source_by_role(scenario, "transfer_log")
    rng = random.Random(seed + _STREAM_TRANSFERS)
    wire_table = transfers["tables"]["movements"]
    wires: list[tuple[Any, ...]] = []
    for index in range(int(counts["transfer_movements"])):
        sender = rng.choice(population)
        beneficiary = rng.choice(population)
        wires.append(
            _row(
                wire_table,
                {
                    "id": f"{prefixes['wire']}-{200000 + index}",
                    "sender": sender["name"],
                    "sender_bic": rng.choice(noise["bics"]),
                    "beneficiary": beneficiary["name"],
                    "beneficiary_bic": rng.choice(noise["bics"]),
                    "beneficiary_address": beneficiary["address"],
                    "amount": _amount(rng, noise["amounts"]["wire"]),
                    "currency": rng.choice(noise["currencies"]),
                    "sent": _iso(
                        epoch
                        + timedelta(
                            days=rng.randrange(activity_days),
                            minutes=rng.randrange(1440),
                        )
                    ),
                    "purpose": rng.choice(noise["purposes"]),
                },
            )
        )
    ring_lines: list[str] = []
    for edge in scenario["ring"]["edges"]:
        origin = members[edge["from"]]["transfer_alias"]
        target = members[edge["to"]]["transfer_alias"]
        sent = _iso(
            epoch + timedelta(days=int(edge["day_offset"]), hours=int(edge["hour"]))
        )
        wires.append(
            _row(
                wire_table,
                {
                    "id": edge["reference"],
                    "sender": origin["name"],
                    "sender_bic": origin["bic"],
                    "beneficiary": target["name"],
                    "beneficiary_bic": target["bic"],
                    "beneficiary_address": target["address"],
                    "amount": edge["amount"],
                    "currency": edge["currency"],
                    "sent": sent,
                    "purpose": edge["purpose"],
                },
            )
        )
        ring_lines.append(
            f"{origin['name']}|{target['name']}|{edge['amount']}|{sent}"
        )
    emit(transfers, transfers_name, {"movements": wires})

    ring_digest = hashlib.sha256()
    for line in sorted(ring_lines):
        ring_digest.update(line.encode("utf-8"))
        ring_digest.update(b"\n")

    # --- registry source: KYC entries for noise + ring --------------------
    registry_name, registry = _source_by_role(scenario, "registry")
    rng = random.Random(seed + _STREAM_REGISTRY)
    registry_table = registry["tables"]["entities"]
    entries: list[tuple[Any, ...]] = []
    for person in population:
        entries.append(
            _row(
                registry_table,
                {
                    "id": person["registry_id"],
                    "name": person["name"],
                    "tax_id": person["tax_id"],
                    "address": person["address"],
                    "jurisdiction": person["jurisdiction"],
                    "registered": _iso(
                        epoch - timedelta(days=rng.randrange(30, history_days))
                    ),
                },
            )
        )
    for member in members.values():
        spec = member["registry"]
        entries.append(
            _row(
                registry_table,
                {
                    "id": spec["id"],
                    "name": spec["name"],
                    "tax_id": spec["tax_id"],
                    "address": spec["address"],
                    "jurisdiction": spec["jurisdiction"],
                    "registered": _iso(
                        epoch + timedelta(days=int(spec["registered_day_offset"]))
                    ),
                },
            )
        )
    emit(registry, registry_name, {"entities": entries})

    return {
        "row_counts": row_counts,
        "checksums": checksums,
        "ring_signature": ring_digest.hexdigest(),
    }
