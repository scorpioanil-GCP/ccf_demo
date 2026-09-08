"""cp-05's spine — the six steps in order, the gates, and the emitted rollup.

[ADAPT] the step sequence. [MECHANISM] the declarations it reads and the gates
it runs.

This program holds no domain value. It reads ``ccf_config.yaml``,
``backends.yaml`` and ``artifacts/`` for every figure it uses, and
``assembler.py`` for every arithmetic decision. What lives here is the ORDER
(spec §D.2) and the four validation gates (spec §D.7).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import asdict
from typing import Any

import psycopg

import assembler as asm
import deployment as dep


def _canonical(payload: dict[str, Any]) -> bytes:
    """Stable bytes for the content address — sorted keys, no whitespace drift."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_address(payload: dict[str, Any]) -> str:
    """The single check worth running.

    A hash over the whole answer, so it only reproduces if every input did — the
    resolved anchor, the limit definition, the family, the dedup and the TTL
    window. One drifted value anywhere and the address differs.

    ``expires_at`` is EXCLUDED (spec §D.4): it is a function of request time
    rather than of the answer, and including it would make every run a different
    product.
    """
    scoped = {k: v for k, v in payload.items() if k != "expires_at"}
    return hashlib.sha256(_canonical(scoped)).hexdigest()


def produce(*, anchor: str | None = None, intent: str | None = None,
            depth: int | None = None, materiality: float | None = None,
            follow_guarantees: bool | None = None,
            follow_cross_default: bool | None = None,
            basis: str | None = None) -> dict[str, Any]:
    """One rollup, assembled through the six steps spec §D.2 declares.

    Every parameter defaults to the DECLARATION, never to a literal in this
    file: the anchor and the demonstration parameters come from
    ``artifacts/question.yaml``, and any omitted request argument falls to
    ``ccf_config.yaml::request_contract.argument_defaults``.
    """
    config = dep.load(dep.CONFIG)
    backends = dep.load(dep.BACKENDS)
    question = dep.load(dep.QUESTION)[dep.DECLARATION]
    ttl = dep.load(dep.TTL)[dep.DECLARATION]

    declared = question["parameters"]
    defaults = config["request_contract"]["argument_defaults"]

    def pick(name: str, supplied: Any) -> Any:
        if supplied is not None:
            return supplied
        if name in declared:
            return declared[name]
        return defaults[name]

    anchor_lei = anchor or question["subject"]
    intent_value = pick("intent", intent)
    depth_value = int(pick("depth", depth))
    materiality_value = float(pick("materiality", materiality))
    flags = {
        "follow_guarantees": bool(pick("follow_guarantees", follow_guarantees)),
        "follow_cross_default": bool(pick("follow_cross_default", follow_cross_default)),
    }
    basis_value = str(pick("basis", basis))

    bounds = config["request_contract"]["argument_bounds"]["depth"]
    if not (bounds["minimum"] <= depth_value <= bounds["maximum"]):
        raise ValueError(
            f"depth {depth_value} is outside the declared bound "
            f"[{bounds['minimum']}, {bounds['maximum']}]. Refused BY NAME, never clamped — "
            "clamping would answer a question the caller did not ask and label it as theirs."
        )

    graph, amounts = dep.resolve_sources(backends)
    schema = amounts.schema

    with psycopg.connect(amounts.dsn, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            # 1 · Resolve
            anchor_lei, anchor_name = asm.resolve_anchor(cur, schema, anchor_lei)
            # 2 · Policy
            limit = asm.load_limit_definition(cur, schema, intent_value)

            # the anchor's node URI, via the ledger's own lei predicate
            rows = dep.sparql(graph, f'SELECT ?s {dep._from_clause(graph)} '
                                     f'WHERE {{ ?s <{dep.LEI_PREDICATE}> "{anchor_lei}" }}')
            anchor_nodes = dep.one_column(rows, "s")
            if not anchor_nodes:
                raise LookupError(
                    f"{anchor_lei} resolves in {schema}.legal_entity but carries no node in "
                    f"ledger {graph.ledger}. The stores disagree about the anchor's existence, "
                    "which is a finding about the estate rather than an empty family."
                )
            anchor_node = anchor_nodes[0]

            # 3 · Traversal — ONE walk, several predicates, both directions
            nodes = asm.walk(graph, anchor_node, depth_value,
                             flags["follow_guarantees"], flags["follow_cross_default"])
            # GATE 1 · empty-operator guard (spec §D.7)
            if not nodes:
                raise AssertionError(
                    "empty-operator guard: the traversal returned no nodes, not even the "
                    "anchor. A step silently produced nothing."
                )

            lei_by_node = asm.node_leis(graph, nodes)

            # 4 · Batch Enrich — ONE query
            books = asm.enrich(cur, schema, sorted(set(lei_by_node.values())))

            # 5 · Aggregate
            rollup = asm.aggregate(cur, schema, anchor_lei, anchor_node, intent_value,
                                   limit, depth_value, nodes, lei_by_node, books,
                                   materiality_value, flags)
            rollup.reconciliation = asm.reconcile(cur, schema, anchor_lei,
                                                  rollup.gross.committed)

    # GATE 4 · reconciliation guard — the one that catches a plausible wrong answer
    asm.reconciliation_guard(rollup)

    # 6 · Contract assembly
    asked_at = _dt.datetime.fromisoformat(question["asked_at"])
    expires_at = asked_at + _dt.timedelta(seconds=int(ttl["declared_ttl_seconds"]))

    # GATE 3 · TTL bounds (spec §D.7)
    window = (expires_at - asked_at).total_seconds()
    if not 0 < window <= int(ttl["max_ttl_seconds"]):
        raise AssertionError(
            f"TTL bounds: window {window}s is outside (0, {ttl['max_ttl_seconds']}]."
        )

    # GATE 2 · lineage strict equality — the record names exactly what ran
    operators_invoked = ["Resolve", "Policy", "Traversal", "Enrich", "Aggregate"]

    payload: dict[str, Any] = {
        "schema_name": config["product_class"]["schema_name"],
        "schema_version": config["product_class"]["schema_version"],
        "anchor": {"lei": rollup.anchor_lei, "legal_name": anchor_name,
                   "node": rollup.anchor_node},
        "intent": rollup.intent,
        "policy_version": rollup.policy_version,
        "policy": {"counts_guarantees": limit.counts_guarantees,
                   "counts_undrawn": limit.counts_undrawn,
                   "connection_basis": limit.connection_basis},
        "request": {"depth": depth_value, "materiality": materiality_value,
                    "basis": basis_value, **flags},
        "family": {"nodes": len(rollup.family_nodes),
                   "members_with_lei": rollup.members_with_lei,
                   "members_holding_facilities": len(
                       [e for e in rollup.entities if e.facility_count])},
        "measures": {"gross": rollup.gross.as_dict(), "adjusted": rollup.adjusted.as_dict()},
        "guarantee_dedup": {"cases": len(rollup.dedup_cases), "detail": rollup.dedup_cases},
        "entities": [
            {"lei": e.lei, "legal_name": e.legal_name, "facilities": e.facility_count,
             "gross": e.gross.as_dict()} for e in rollup.entities],
        "connected_without_exposure": rollup.connected_without_exposure,
        "findings": rollup.findings,
        "reconciliation": rollup.reconciliation,
        "lineage": {"operators_invoked": operators_invoked,
                    "graph_snapshot_ledger": graph.ledger,
                    "policy_version": rollup.policy_version,
                    "asked_at": question["asked_at"]},
        "expires_at": expires_at.isoformat(),
    }
    payload["content_address"] = content_address(payload)
    return payload


if __name__ == "__main__":  # pragma: no cover - module entry point
    print(json.dumps(produce(), indent=2))
