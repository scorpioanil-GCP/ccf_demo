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
import pathlib
import tempfile
from decimal import Decimal
from dataclasses import asdict
from typing import Any

import psycopg

from ccf.products.contract import ContextProductContract

import assembler as asm
import deployment as dep


#: The tenant this deployment declares. Read, never written here.
_TENANT = dep.load(dep.CONFIG)["tenant_id"]


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

    anchor_lei = anchor or question["subject"]
    # `intent` is a TOP-LEVEL ProductRequest field, not an argument (the SDK
    # refuses a contract that declares it under `arguments.properties`), so it
    # is picked here and everything else is RESOLVED below.
    intent_value = intent or question["parameters"]["intent"]

    # ------------------------------------------------------------------
    # EVERY OTHER PARAMETER IS RESOLVED BY THE SDK, WITH ITS AUTHORITY.
    # ------------------------------------------------------------------
    #
    # `policy > caller > default`, bounded by `technical`. Nothing in this file
    # picks a value: `deployment.effective_request` hands the caller's supplied
    # values, the class defaults, the registered policy constraints and the
    # backend capabilities to `resolve_effective_request`, and the OUTCOME is
    # what this product serves.
    #
    # 5% IS THE PRODUCT DEFAULT, NOT THE PRODUCT TRUTH. The truth is "return
    # family exposures above the EFFECTIVE materiality threshold", and the
    # effective threshold is resolved per request. Three callers wanting 2%, 5%
    # and 10% are three parameterizations of one product, not three products.
    with tempfile.TemporaryDirectory() as scratch:
        _fabric, registry = dep.boot(pathlib.Path(scratch))
        outcome = dep.effective_request(
            config=config, registry=registry,
            supplied={
                "depth": depth,
                "materiality": None if materiality is None else Decimal(str(materiality)),
                "follow_guarantees": follow_guarantees,
                "follow_cross_default": follow_cross_default,
                "basis": basis,
            },
            subject=anchor_lei, intent=intent_value,
            freshness=question["freshness"],
            asked_at=_dt.datetime.fromisoformat(question["asked_at"]),
        )

    if outcome.refusal is not None:
        detail = getattr(outcome.refusal, "detail", None) or getattr(
            outcome.refusal, "reason", str(outcome.refusal))
        bound = getattr(outcome.refusal, "bound", None)
        authority = f" [authority: {bound.authority}]" if bound is not None else ""
        raise ValueError(f"{detail}{authority}")

    effective = {p.name: p for p in outcome.evidence.parameters}
    depth_value = int(effective["depth"].value)
    materiality_value = float(effective["materiality"].value)
    flags = {
        "follow_guarantees": bool(effective["follow_guarantees"].value),
        "follow_cross_default": bool(effective["follow_cross_default"].value),
    }
    basis_value = str(effective["basis"].value)

    graph, amounts = dep.resolve_sources(backends)
    schema = amounts.schema
    asked_at = _dt.datetime.fromisoformat(question["asked_at"])

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

            # 3 · Traversal — THROUGH THE FABRIC, not around it.
            #
            # ACQUISITION first: read the source estate over SPARQL. Backend-
            # specific by nature, and with no SDK surface today (`D-IMPL-277`,
            # open). It populates L3 and does NOT answer the question.
            acquired = asm.walk(graph, anchor_node, depth_value,
                                flags["follow_guarantees"], flags["follow_cross_default"])
            edges = asm.acquire_edges(graph, acquired,
                                      flags["follow_guarantees"], flags["follow_cross_default"])
            lei_by_node = asm.node_leis(graph, acquired)

            # DECISION LOGIC second: admit through L2's single writer, then let
            # the operator the Control Plane REGISTERED decide the family, over
            # a GraphView of L3 bounded at the request's own instant.
            with tempfile.TemporaryDirectory() as fabric_root:
                fabric, _registry = dep.boot(pathlib.Path(fabric_root))
                traversed = dep.populate_and_traverse(
                    fabric=fabric, graph=graph, anchor_node=anchor_node,
                    nodes=acquired, edges=edges, leis=lei_by_node, asked_at=asked_at,
                )

            nodes = acquired
            family_size = traversed["family_size"]

            # GATE 1 · empty-operator guard (spec §D.7) — now over the OPERATOR's
            # output, which is what the product serves. Guarding the acquisition
            # walk instead would have passed on a populated source while the
            # declared traversal returned nothing.
            if family_size == 0:
                raise AssertionError(
                    "empty-operator guard: the declared traversal operator returned no "
                    f"entities over an L3 holding {len(acquired)} ingested nodes and "
                    f"{len(edges)} relationship claims. A step silently produced nothing."
                )

            # 4 · Batch Enrich — ONE query, over the LEIs the OPERATOR reached
            books = asm.enrich(cur, schema, traversed["family_leis"])

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
        # THE EFFECTIVE REQUEST, WITH AUTHORITY PER PARAMETER. This is what
        # makes the answer replayable as an answer to a QUESTION rather than as
        # a set of numbers: a reader can tell whether 5% was the product's
        # default, this caller's choice, or a policy ceiling that overrode them.
        "effective_request": {
            p.name: {"value": str(p.value), "authority": p.authority,
                     "source": f"{p.source.kind}/{p.source.identity}"}
            for p in outcome.evidence.parameters
        },
        "family": {"nodes": family_size,
                   "acquired_from_source": len(acquired),
                   "relationship_claims_admitted": len(edges),
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
                    "traversal_operator": "traversal.typed-neighborhood",
                    "graph_snapshot_ledger": graph.ledger,
                    "policy_version": rollup.policy_version,
                    "asked_at": question["asked_at"]},
        "expires_at": expires_at.isoformat(),
    }
    payload["content_address"] = content_address(payload)
    return payload


def as_contract(payload: dict[str, Any]) -> "ContextProductContract":
    """The same answer as the SDK's TYPED contract — `extra=forbid`, nine fields.

    Kept beside :func:`produce` rather than replacing it, because the two serve
    different readers. `produce` returns a plain mapping a transcript can render
    and a test can diff; this returns the object the L6 delivery surfaces
    require, and it is what the MCP door serves.

    **The contract surface turned out to be small.** Nine required fields and a
    three-field lineage, and `ttl_anchor` is a `Literal` that already carries
    `from_decision` — this product's anchor needed no SDK change to express.
    Recorded because the door around it is not small (spec §F.4), and the
    contrast is the useful measurement: the CONTRACT is cheap, the GOVERNED
    DOOR is not.
    """
    from ccf.products.contract import ContextProductContract, ProductLineage

    lin = payload["lineage"]
    asked_at = _dt.datetime.fromisoformat(lin["asked_at"])
    return ContextProductContract(
        schema_name=payload["schema_name"],
        schema_version=payload["schema_version"],
        # The plan the answer came from, not a run id: two asks of the same
        # question under the same policy share it, which is what makes the
        # content address the thing that distinguishes runs.
        plan_id=payload["content_address"][:16],
        tenant_id=_TENANT,
        # `from_decision` (spec §B.1 element 3): the boundary IS the ask.
        temporal_boundary=asked_at,
        expires_at=_dt.datetime.fromisoformat(payload["expires_at"]),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset(lin["operators_invoked"]),
            policy_bundle_versions=frozenset({lin["policy_version"]}),
            # The ledger read is the graph snapshot. Fluree's `t` is TRANSACTION
            # time and `D-IMPL-88` rules it must not back `as_of`; it is recorded
            # BESIDE this boundary, never inside it.
            graph_snapshot_at=asked_at,
        ),
        payload=payload,
    )


if __name__ == "__main__":  # pragma: no cover - module entry point
    print(json.dumps(produce(), indent=2))
