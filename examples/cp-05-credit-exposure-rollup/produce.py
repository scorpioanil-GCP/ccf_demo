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

from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.gates import ServableProduct, refuse_over_tolerance, run_gates

import assembler as asm
import deployment as dep
import projection as proj


#: The tenant this deployment declares. Read, never written here.
_TENANT = dep.load(dep.CONFIG)["tenant_id"]


def _perspective(config: dict[str, Any]):
    """The deployment's declared perspective — Π's role conditioning."""
    from ccf.projection.plan import Perspective

    declared = config["default_perspective"]
    return Perspective(principal_id=declared["principal_id"], role=declared["role"])


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


class RequestRefused(ValueError):
    """The request boundary refused before any assembly ran.

    Carried as a type rather than a message so a caller demonstrating several
    consumers can render the refusal instead of dying on it. **This is not the
    tolerance refusal**: this one happens before the fabric reads anything,
    because the caller asked for something the class or a policy will not
    resolve. The tolerance refusal happens after a product EXISTS.
    """

    def __init__(self, detail: str, refusal: Any) -> None:
        super().__init__(detail)
        self.refusal = refusal


def produce(*, anchor: str | None = None, intent: str | None = None,
            depth: int | None = None, materiality: float | None = None,
            follow_guarantees: bool | None = None,
            follow_cross_default: bool | None = None,
            basis: str | None = None,
            debt_tolerance: str | None = None,
            as_of: str | None = None) -> dict[str, Any]:
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
                # THE CONSUMER'S FITNESS BAR, folded here and nowhere else.
                # Text in, `Decimal` on the wire, for the same reason the
                # declared defaults are quoted: a float tolerance would make
                # the comparison against D_c platform-dependent.
                "debt_tolerance": (
                    None if debt_tolerance is None else Decimal(str(debt_tolerance))
                ),
                # DECLARED AND INERT (`artifacts/question.yaml`). Passed through
                # deliberately so the refusal is the SDK's, by name, rather than
                # this file quietly dropping an argument the caller supplied.
                "as_of": as_of,
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
        raise RequestRefused(f"{detail}{authority}", outcome.refusal)

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
                # The CONTROL PLANE registry, held rather than discarded: the
                # gate run below and the operator resolution above must reach
                # the SAME one, or the gates would be reading a class some
                # other registry pinned.
                fabric, control_plane = dep.boot(pathlib.Path(fabric_root))
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

            # 5 · Aggregate — COMPLETE FAMILY TRUTH, no threshold applied.
            rollup = asm.aggregate(cur, schema, anchor_lei, anchor_node, intent_value,
                                   limit, depth_value, nodes, lei_by_node, books, flags)
            rollup.reconciliation = asm.reconcile(cur, schema, anchor_lei,
                                                  rollup.gross.committed)

            # EVIDENCE for the debt assessment, gathered from what the estate
            # attests rather than from what the answer looks like.
            family_leis = traversed["family_leis"]
            cur.execute(
                f"SELECT facility_id, balance_as_of FROM {schema}.facility "
                f"WHERE borrower_lei = ANY(%s) AND balance_as_of IS NOT NULL",
                (family_leis,))
            balance_observations = [
                (fid, _dt.datetime.combine(when, _dt.time(), tzinfo=_dt.timezone.utc)
                 if not isinstance(when, _dt.datetime) else when)
                for fid, when in cur.fetchall()
            ]
            cur.execute(
                f"SELECT lei, plausible FROM {schema}.debt_reconciliation "
                f"WHERE lei = ANY(%s)", (family_leis,))
            reconciliation_rows = list(cur.fetchall())
            # A genuine enrich FAILURE, not "found no facilities". The batch
            # query answered for every LEI it was given; a member with an LEI
            # and no facility is a DETERMINED answer of zero.
            enrich_failures = len([lei for lei in family_leis if lei not in books
                                   and lei is None])

    # GATE 4 · reconciliation guard — the one that catches a plausible wrong answer
    asm.reconciliation_guard(rollup)

    # ------------------------------------------------------------------
    # L5 · Π — WHICH OF THAT TRUTH IS RELEVANT TO THIS CALLER
    # ------------------------------------------------------------------
    #
    # The plan is constructed with the EFFECTIVE threshold and applies it. It is
    # NOT told which authority won: that is recorded on the contract's effective
    # request and travels into replay, an audit fact rather than an input. A
    # projection branching on provenance would let authority change the answer.
    # ------------------------------------------------------------------
    # CONTEXT DEBT — from evidence, before any projection is chosen.
    # ------------------------------------------------------------------
    #
    # Assessed BEFORE L5 runs, deliberately: debt describes confidence in the
    # assembled truth, and the caller's threshold cannot make that truth more or
    # less trustworthy. The same evidence yields the same debt at 2%, 5% or 10%.
    debt_assessment, debt_evidence = dep.assess_context_debt(
        fabric=traversed["fabric"],
        balance_observations=balance_observations,
        reconciliation_rows=reconciliation_rows,
        family_size=traversed["family_size"],
        checkable_members=len(traversed["family_leis"]),
        enrich_failures=enrich_failures,
        asked_at=asked_at,
    )

    plan = proj.ExposureRollupProjection(
        plan_id=f"cp-05.exposure-rollup/materiality={materiality_value}",
        threshold=materiality_value,
        entities=rollup.entities,
        gross_committed=rollup.gross.committed,
        connected_without_exposure=rollup.connected_without_exposure,
    )
    # THROUGH THE ENGINE, not by calling the plan directly. `ProjectionEngine`
    # runs the two-stage execution the whitepaper specifies — operator plan,
    # then projection plan — and hands back what it OBSERVED ITSELF RUNNING
    # rather than what this program declared. That observed set is what lineage
    # carries and what a gate would check declared-against-observed.
    from ccf.projection.engine import ProjectionEngine

    execution = ProjectionEngine(
        reader=traversed["fabric"].handle.reader, registry=traversed["registry"]
    ).execute(
        plan=plan,
        perspective=_perspective(config),
        tenant_id=config["tenant_id"],
        temporal_boundary=asked_at,
    )
    projected = execution.projection

    # 6 · Contract assembly
    asked_at = _dt.datetime.fromisoformat(question["asked_at"])
    expires_at = asked_at + _dt.timedelta(seconds=int(ttl["declared_ttl_seconds"]))

    # GATE 3 · TTL bounds (spec §D.7)
    window = (expires_at - asked_at).total_seconds()
    if not 0 < window <= int(ttl["max_ttl_seconds"]):
        raise AssertionError(
            f"TTL bounds: window {window}s is outside (0, {ttl['max_ttl_seconds']}]."
        )

    # GATE 2 · lineage strict equality — the record names exactly what ran.
    #
    # The FABRIC operators come from the engine's OWN observation
    # (`ExecutionResult.operators_invoked`), never from a list this file
    # maintains: a hand-kept list is a declaration that drifts, and lineage
    # strict equality would then be comparing a claim against itself. The
    # assembly steps that are not registry operators are named beside them —
    # Resolve, Enrich and Aggregate are assembly stages, not operators
    # (`ccf_config.yaml` records why).
    operators_invoked = sorted(execution.operators_invoked) + [
        "Resolve", "Enrich", "Aggregate"
    ]

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
        # WHAT L5 DECIDED, under this caller's effective threshold. The family
        # above is the same for every caller; this block is not.
        "projection": {"plan_id": projected.plan_id, **dict(projected.payload)},
        "entities": list(projected.payload["material"]),
        "connected_without_exposure": rollup.connected_without_exposure,
        "findings": rollup.findings,
        "reconciliation": rollup.reconciliation,
        # THE ASSESSMENT, NEVER A VERDICT. Whether this figure refuses a request
        # is a fulfillment determination against a tolerance, made downstream.
        "context_debt": {
            "debt": str(debt_assessment.debt),
            "signal": debt_assessment.signal.value
            if hasattr(debt_assessment.signal, "value") else str(debt_assessment.signal),
            "evidence": debt_evidence,
        },
        "lineage": {"operators_invoked": operators_invoked,
                    "traversal_operator": "traversal.typed-neighborhood",
                    "projection_plan_id": execution.plan_id,
                    "engine_observed_operators": sorted(execution.operators_invoked),
                    "graph_snapshot_ledger": graph.ledger,
                    "policy_version": rollup.policy_version,
                    "asked_at": question["asked_at"]},
        "expires_at": expires_at.isoformat(),
    }
    payload["content_address"] = content_address(payload)

    # ==================================================================
    # THE GOVERNED FULFILLMENT DETERMINATION — the last step, and a
    # SEPARATE one from everything above it.
    # ==================================================================
    #
    # The order is fixed and each arrow is a different kind of judgment:
    #
    #   assembly -> projection -> Debt assessment -> effective Debt
    #   tolerance -> fulfillment determination -> replay -> disclosure
    #
    # **Context Debt does not refuse the request.** Debt is a MEASUREMENT of
    # the fabric's confidence in what it assembled. Governance uses that
    # measurement to decide whether fulfillment is permitted. The two live in
    # different objects for that reason: `DebtAssessment` is above, in
    # `payload["context_debt"]`, and it is the same number for every consumer;
    # `refuse_over_tolerance` is below, and it is the only thing that can vary
    # between two consumers holding the same determination.
    #
    # WHY THE GATES COME FIRST. `refuse_over_tolerance` takes a
    # `ServableProduct`, which is not constructible outside `run_gates`
    # (INV-CH7-52). The sequencing is therefore STRUCTURAL rather than
    # documented: a caller who has not run the gates has nothing to pass, so
    # "withheld" can only ever be said about a product that exists.
    product_class = dep.register_class(registry=control_plane, config=config, ttl=ttl)
    candidate = ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id=execution.plan_id,
        tenant_id=_TENANT,
        temporal_boundary=asked_at,
        expires_at=expires_at,
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            # THE ENGINE'S OWN OBSERVATION, not the list rendered in the
            # payload. Gate 2 holds declared against observed in BOTH
            # directions, so the assembly-stage names beside them in
            # `payload["lineage"]` — Resolve, Enrich, Aggregate — cannot ride
            # in here: they are stages, not registry operators, and declaring
            # one that never ran is exactly what gate 2 refuses.
            operators_invoked=frozenset(execution.operators_invoked),
            policy_bundle_versions=frozenset({rollup.policy_version}),
            graph_snapshot_at=asked_at,
        ),
        payload=payload,
        # THE ASSESSMENT TRAVELS ON THE PRODUCT. Without it the tolerance check
        # has nothing to compare against and withholds for that reason — which
        # is the right answer to "the tolerance cannot be shown to be met",
        # rather than a permissive default.
        debt=debt_assessment,
    )
    # `now` IS THE PINNED INSTANT, NOT THE WALL CLOCK. This product's anchor is
    # `from_decision`: the window opens when the question is asked. Evaluating a
    # pinned demonstration against today's clock would refuse on `ttl-bounds`
    # every time — correctly, and about the transcript rather than the product.
    gated = run_gates(
        candidate,
        engine_resolved=execution.operators_invoked,
        now=asked_at,
        registry=control_plane,
        product_class=product_class,
    )
    if not isinstance(gated, ServableProduct):
        raise AssertionError(f"the validation gates refused this product: {gated}")

    # ONE ARGUMENT, AND IT IS A RESOLVED PARAMETER RATHER THAN A NUMBER. The
    # three debt authorities — the class default, this caller's declaration and
    # any applicable policy constraint — were folded exactly ONCE, upstream, by
    # `resolve_effective_request`. Handing a float here would be a second fold,
    # and a second fold is where a product quietly re-acquires the power to
    # overrule its own governance.
    withheld = refuse_over_tolerance(gated, tolerance=effective.get("debt_tolerance"))

    tolerance = effective.get("debt_tolerance")
    payload["fulfillment"] = {
        "served": withheld is None,
        "tolerance": None if tolerance is None else str(tolerance.value),
        "tolerance_authority": None if tolerance is None else tolerance.authority,
        "observed_debt": str(debt_assessment.debt),
        "detail": None if withheld is None else withheld.detail,
    }
    # DELIBERATELY AFTER THE CONTENT ADDRESS, and the reason is that the
    # outcome is REDUNDANT with what the address already covers. The address
    # spans the effective request — including the resolved `debt_tolerance` and
    # the authority that set it — and the observed Debt. Served-or-withheld is a
    # pure function of those two, so hashing it in would only restate them.
    #
    # WHAT DOES CHANGE THE ADDRESS, MEASURED: two consumers differing only in
    # fitness get DIFFERENT addresses, because they asked different questions —
    # "give me this if you are confident enough" is not "give me this whatever
    # your confidence." What they get back is the SAME DETERMINATION: family 77,
    # gross 10,125,000,000, adjusted 9,325,000,000 and D_c 1.000 are byte-equal
    # across every consumer in `run.py`'s scenario set. The fabric does not
    # revise what it knows to suit who is asking; it revises only whether it is
    # willing to attest that what it knows is fit to act on.
    return payload


def as_contract(payload: dict[str, Any]) -> "ContextProductContract":
    """The same answer as the SDK's TYPED contract — `extra=forbid`, nine fields.

    Kept beside :func:`produce` rather than replacing it, because the two serve
    different readers. `produce` returns a plain mapping a transcript can render
    and a test can diff; this returns the object the L6 delivery surfaces
    require, and it is what the MCP door serves. It reconstructs the SAME
    candidate `produce` gated, from the same payload.

    **`fulfillment` IS STRIPPED, AND THAT IS THE POINT.** Whether this product
    was served or withheld is a determination made ABOUT the contract, by
    `refuse_over_tolerance`, after the gates admitted it. It is not a field of
    the contract and must not become one: a product that carried its own
    fulfillment outcome would be a product that had already decided whose
    tolerance applied, and two consumers with different fitness bars would then
    need two contracts for one determination.

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
    determination = {k: v for k, v in payload.items() if k != "fulfillment"}
    return ContextProductContract(
        schema_name=payload["schema_name"],
        schema_version=payload["schema_version"],
        # The plan the answer came from, not a run id: two asks of the same
        # question under the same policy share it, which is what makes the
        # content address the thing that distinguishes runs.
        plan_id=lin["projection_plan_id"],
        tenant_id=_TENANT,
        # `from_decision` (spec §B.1 element 3): the boundary IS the ask.
        temporal_boundary=asked_at,
        expires_at=_dt.datetime.fromisoformat(payload["expires_at"]),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            # THE ENGINE-OBSERVED SET, matching what gate 2 held the candidate
            # to. `lineage.operators_invoked` in the payload additionally names
            # the assembly stages for a human reader; those are not registry
            # operators and gate 2 would refuse them.
            operators_invoked=frozenset(lin["engine_observed_operators"]),
            policy_bundle_versions=frozenset({lin["policy_version"]}),
            # The ledger read is the graph snapshot. Fluree's `t` is TRANSACTION
            # time and `D-IMPL-88` rules it must not back `as_of`; it is recorded
            # BESIDE this boundary, never inside it.
            graph_snapshot_at=asked_at,
        ),
        payload=determination,
    )


if __name__ == "__main__":  # pragma: no cover - module entry point
    print(json.dumps(produce(), indent=2))
