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
from typing import Any

import psycopg

# WHAT THIS MODULE STILL IMPORTS FROM THE SDK, AND WHY IT IS THIS SHORT.
#
# `24.11`'s migration (`D-IMPL-298`) moved the governed spine into
# `ccf.products.resolver::GovernedResolver`, and these imports went with the
# responsibility rather than with the symbol. Gone: `run_gates`,
# `ServableProduct`, `refuse_over_tolerance`, `envelope_for`,
# `RefusalEvidence`, `RequestIdentity`, `ReplayRefusalRecorder`,
# `build_replay_record`, `DecisionReplayRecord`, `PolicyBinding`,
# `ProvenanceSource`, `serve` and `ProjectionEngine` — thirteen SDK surfaces
# this file used to compose by hand and now composes not at all.
#
# What remains is TYPES, for `as_contract` below: a renderer and a test need to
# read a served product's shape, and reading a shape is not composing a path.
from ccf.products.contract import ContextProductContract, ProductLineage

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


#: The key the limit definition binds under in the replay record. It names a
#: versioned credit policy read from the amounts store — NOT a Control Plane
#: artifact, which is why the version beside it is a `limit_definition` row id
#: rather than a pin. `ccf_config.yaml` cannot hold it: the Control Plane
#: document's section vocabulary is closed (see `artifacts/replay.yaml`).
LIMIT_DEFINITION_BINDING = "limit_definition"


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


def _replay_record(governed: Any, *, store_root: pathlib.Path) -> Any:
    """The Decision Replay record ``governed`` names, or ``None``.

    ``None`` when the outcome carries no reference — a refusal minted by a seam
    that recorded none says so with
    :data:`~ccf.products.refusal.NO_REPLAY_REFERENCE` — or when the store
    cannot resolve it. Read while the store is still alive; see the call site.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.replay.record import DecisionReplayRecord

    reference = getattr(governed, "replay_ref", None)
    address = getattr(reference, "content_address", None)
    if address is None:
        return None
    store = FileArtifactStore(root=store_root)
    try:
        return DecisionReplayRecord.model_validate_json(
            store.get(content_address=address)
        )
    except (KeyError, LookupError, OSError, ValueError):
        return None


def produce(**kwargs: Any) -> dict[str, Any]:
    """The payload alone — what a transcript renders and a test diffs.

    A thin wrapper over :func:`produce_governed`, which additionally hands back
    the GOVERNED RESULT: the `ServedProduct` or the recorded, disclosed
    `RefusalEnvelope`. Two callers want two things and neither should carry the
    other's — `run.py` renders figures, and the MCP door releases a typed
    governed result and nothing else (`D-IMPL-260` P-A).
    """
    return produce_governed(**kwargs)[0]



def produce_governed(
    *, anchor: str | None = None, intent: str | None = None,
    depth: int | None = None, materiality: str | None = None,
    follow_guarantees: bool | None = None,
    follow_cross_default: bool | None = None,
    basis: str | None = None,
    debt_tolerance: str | None = None,
    as_of: str | None = None,
    replay_root: pathlib.Path | None = None,
) -> tuple[dict[str, Any], Any, Any]:
    """One rollup, through ``GovernedResolver``. cp-05 assembles; CCF governs.

    **The whole of what this function does** is boot, assemble the domain truth,
    hand the SDK its extension points, and call it. Everything between the
    assembled rollup and the delivered result — the validation gates, contract
    construction, Context Debt placement, the fulfillment determination, refusal
    shaping, the replay record and the serve — belongs to
    :class:`~ccf.products.resolver.GovernedResolver` and appears nowhere here.
    :func:`produce_governed` above is the hand-composed spine this replaces.

    **The architecture, ruled at** ``D-IMPL-299``::

        source acquisition -> L2 admission/enrichment -> L3 governed state
          -> L4 family traversal/aggregation -> L5 materiality projection

    and its semantic rule: *"L5 may select, shape, and present truth. It must
    not reach back to a system of record to create truth."* So Postgres is read
    HERE, before Π, and the gross/adjusted determination is complete before the
    resolver is called. The projection receives assembled truth and applies the
    effective threshold to it.

    **Why the request is resolved twice, stated rather than hidden.** The
    resolution below parameterises ACQUISITION — the walk cannot know its depth
    or its edge flags until it knows what the caller effectively asked. The
    resolver then resolves again, and that second resolution is the one that
    GOVERNS: it is what reaches replay dimension 2 with each parameter's
    authority. Same pure function over the same inputs, so the two agree by
    construction; they differ in purpose, not in value. This is calling the
    SDK's resolution, never reimplementing it.

    **No ``effective_request`` in the payload.** Which authority supplied each
    value is recorded on the governed envelope — ``PolicyBindingsSnapshot.
    request_resolution`` carries the full :class:`~ccf.products.provenance.
    EffectiveRequest`, every parameter with its ``authority`` — and a business
    payload that restated it would be reconstructing governance state the
    fabric already owns. It also keeps the content address a function of the
    business answer alone: two callers whose parameters resolved by different
    authorities to the same effective values get the same payload address, and
    the replay record is what tells their determinations apart.
    """
    config = dep.load(dep.CONFIG)
    backends = dep.load(dep.BACKENDS)
    question = dep.load(dep.QUESTION)[dep.DECLARATION]
    ttl = dep.load(dep.TTL)[dep.DECLARATION]

    anchor_lei = anchor or question["subject"]
    intent_value = intent or question["parameters"]["intent"]

    # THE FAMILY TOKEN, READ ONCE AND USED TWICE — and that is the point.
    #
    # `D-IMPL-295` made `families` a required request argument bound to the
    # policy operator's `permitted_classifications`. The SAME token is what
    # `populate_and_traverse` stamps on every admitted entity as `family_id`.
    # Reading it from one place is what keeps the two in step: a request asking
    # for a family nobody was admitted under would serve an honest family of
    # zero, which is exactly the confidently-wrong answer `24.10-F-11` was.
    family_token = str(question["parameters"]["families"][0])

    # --8<-- [start:boot]
    # 1 · WHAT THE CALLER EFFECTIVELY ASKED — to parameterise acquisition.
    with tempfile.TemporaryDirectory() as scratch:
        _scratch_fabric, scratch_registry = dep.boot(pathlib.Path(scratch))
        # --8<-- [end:boot]
        product_request, outcome = dep.effective_request(
            config=config, registry=scratch_registry,
            supplied={
                "depth": depth,
                # THE LEXICAL VALUE, HANDED OVER UNCONVERTED (`D-IMPL-302`).
                #
                # These two read `Decimal(str(value))` until the SDK gained its
                # contract-aware decode. The conversion was unguarded, and the
                # malformed-value control found what that cost: `Decimal("NaN")`
                # is a perfectly constructible non-finite decimal, and it
                # reached canonicalization as an uncaught
                # `CanonicalizationError` — a runtime failure with no governed
                # refusal and no replay, where a caller deserved a
                # `type-mismatch` naming the parameter.
                #
                # The SDK now converts, because it is the party holding the
                # declaration that says which arguments are numbers. A
                # canonical decimal becomes an exact `Decimal`; anything else
                # passes through untouched and `refuse_request` refuses it BY
                # NAME. Converting here would take that judgment back.
                "materiality": materiality,
                "follow_guarantees": follow_guarantees,
                "follow_cross_default": follow_cross_default,
                "basis": basis,
                "debt_tolerance": debt_tolerance,
                "as_of": as_of,
                "families": [family_token],
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
    materiality_value = effective["materiality"].value
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
            anchor_lei, anchor_name = asm.resolve_anchor(cur, schema, anchor_lei)
            limit = asm.load_limit_definition(cur, schema, intent_value)

            # --8<-- [start:acquire]
            # 2 · ACQUISITION — the source estate, bounded by the caller's walk.
            rows = dep.sparql(graph, f'SELECT ?s {dep._from_clause(graph)} '
                                     f'WHERE {{ ?s <{dep.LEI_PREDICATE}> "{anchor_lei}" }}')
            anchor_nodes = dep.one_column(rows, "s")
            if not anchor_nodes:
                raise LookupError(
                    f"{anchor_lei} resolves in {schema}.legal_entity but carries no node "
                    f"in ledger {graph.ledger}. The stores disagree about the anchor's "
                    "existence, which is a finding about the estate rather than an "
                    "empty family."
                )
            anchor_node = anchor_nodes[0]
            acquired = asm.walk(graph, anchor_node, depth_value,
                                flags["follow_guarantees"], flags["follow_cross_default"])
            edges = asm.acquire_edges(graph, acquired,
                                      flags["follow_guarantees"],
                                      flags["follow_cross_default"])
            lei_by_node = asm.node_leis(graph, acquired)

            # 3 · ASSEMBLY — L2 admission, then the declared L4 walk, then the
            #     complete family truth. THE FABRIC STAYS OPEN past this block:
            #     the resolver reads L3 through it.
            fabric_root = tempfile.TemporaryDirectory()
            try:
                fabric, control_plane = dep.boot(pathlib.Path(fabric_root.name))
                traversed = dep.populate_and_traverse(
                    fabric=fabric, graph=graph, anchor_node=anchor_node,
                    nodes=acquired, edges=edges, leis=lei_by_node,
                    asked_at=asked_at, family=family_token,
                )
                family_size = traversed["family_size"]
                family_leis = traversed["family_leis"]
                books = asm.enrich(cur, schema, family_leis)

                # GROSS AND ADJUSTED ARE DETERMINED HERE, BEFORE Π.
                rollup = asm.aggregate(cur, schema, anchor_lei, anchor_node,
                                       intent_value, limit, depth_value, acquired,
                                       lei_by_node, books, flags)
                rollup.reconciliation = asm.reconcile(cur, schema, anchor_lei,
                                                      rollup.gross.committed)

                # EVIDENCE for the debt assessment, gathered from what the
                # estate attests rather than from what the answer looks like.
                # Transcribed from the legacy spine unchanged — this is domain
                # measurement, not governance, and `D-IMPL-298` preserves it.
                cur.execute(
                    f"SELECT facility_id, balance_as_of FROM {schema}.facility "
                    f"WHERE borrower_lei = ANY(%s) AND balance_as_of IS NOT NULL",
                    (family_leis,))
                balance_observations = [
                    (fid, _dt.datetime.combine(when, _dt.time(),
                                               tzinfo=_dt.timezone.utc)
                     if not isinstance(when, _dt.datetime) else when)
                    for fid, when in cur.fetchall()
                ]
                cur.execute(
                    f"SELECT lei, plausible FROM {schema}.debt_reconciliation "
                    f"WHERE lei = ANY(%s)", (family_leis,))
                reconciliation_rows = list(cur.fetchall())
                # A genuine enrich FAILURE, not "found no facilities". The batch
                # query answered for every LEI it was given; a member with an
                # LEI and no facility is a DETERMINED answer of zero.
                enrich_failures = len([lei for lei in family_leis
                                       if lei not in books and lei is None])

                assessment, _evidence = dep.assess_context_debt(
                    fabric=fabric, balance_observations=balance_observations,
                    reconciliation_rows=reconciliation_rows,
                    family_size=family_size, checkable_members=len(family_leis),
                    enrich_failures=enrich_failures, asked_at=asked_at,
                )

                business = _business_payload(
                    config=config, rollup=rollup, limit=limit,
                    anchor_name=anchor_name, family_size=family_size,
                    basis_value=basis_value, depth_value=depth_value,
                    materiality=materiality_value, flags=flags,
                    acquired_count=len(acquired), edge_count=len(edges),
                )
                # --8<-- [end:acquire]

                # The declared replay binding names a `store_dirname`, which
                # is half a location; the SDK refuses to root a deployment's
                # decision records at whichever directory the process started
                # in (`R-12`). The caller's root, or an ephemeral one beside
                # the fabric — the same default the legacy spine used.
                store_root = replay_root or pathlib.Path(fabric_root.name)
                governed = _governed(
                    fabric=fabric, control_plane=control_plane, config=config,
                    ttl=ttl, rollup=rollup, business=business,
                    materiality=materiality_value, assessment=assessment,
                    product_request=product_request, store_root=store_root,
                )
                # `D-IMPL-309`: the store head the reads ran against is
                # EXECUTION PROVENANCE, recorded in replay dimension 1 and no
                # longer on the product. Read HERE, while the store is still
                # alive — when no `--replay-root` was given it lives under
                # `fabric_root` and is deleted by the cleanup below, so a
                # renderer that tried to resolve it afterwards would find
                # nothing. The transcript therefore gets the record itself
                # rather than reaching for a field that has correctly stopped
                # existing on the vessel.
                record = _replay_record(governed, store_root=store_root)
            finally:
                fabric_root.cleanup()

    payload = dict(getattr(governed, "product", None).payload) if getattr(
        governed, "product", None) is not None else {}
    return payload, governed, record


def _business_payload(*, config, rollup, limit, anchor_name, family_size,
                      basis_value, depth_value, materiality, flags,
                      acquired_count, edge_count) -> dict[str, Any]:
    """cp-05's assembled answer. No governance metadata, by ruling.

    ``effective_request`` is deliberately absent (`D-IMPL-299`): the governed
    envelope owns which authority supplied each value.
    """
    return {
        "schema_name": config["product_class"]["schema_name"],
        "schema_version": config["product_class"]["schema_version"],
        "anchor": {"lei": rollup.anchor_lei, "legal_name": anchor_name,
                   "node": rollup.anchor_node},
        "intent": rollup.intent,
        "policy_version": rollup.policy_version,
        "policy": {"counts_guarantees": limit.counts_guarantees,
                   "counts_undrawn": limit.counts_undrawn,
                   "connection_basis": limit.connection_basis},
        # THE ANSWER'S OWN SCOPE — business content, not governance metadata.
        #
        # These are the parameters that decide WHICH answer this is. cp-05's own
        # config says depth is *"part of PRODUCT IDENTITY, not a tuning knob —
        # the family is 21 nodes at depth 1, 46 at depth 2 and 77 at depth 3, so
        # two depths are two answers"*. A reader holding the payload has to be
        # able to say what it is an answer TO.
        #
        # Deliberately NOT `effective_request`: no authorities appear here.
        # Which authority supplied each value — caller, product default or
        # policy — is the governed envelope's, recorded once in replay
        # dimension 2 (`D-IMPL-299`). The distinction is the whole boundary:
        # the scope is a fact about the answer; the authority is a fact about
        # how the question was governed.
        "request": {
            "depth": depth_value,
            "materiality": str(materiality),
            "basis": basis_value,
            **flags,
        },
        "basis": basis_value,
        "family": {"nodes": family_size,
                   "acquired_from_source": acquired_count,
                   "relationship_claims_admitted": edge_count,
                   "members_with_lei": rollup.members_with_lei,
                   "members_holding_facilities": len(
                       [e for e in rollup.entities if e.facility_count])},
        "measures": {"gross": rollup.gross.as_dict(),
                     "adjusted": rollup.adjusted.as_dict()},
        "guarantee_dedup": {"cases": len(rollup.dedup_cases),
                            "detail": rollup.dedup_cases},
        "connected_without_exposure": rollup.connected_without_exposure,
        "findings": rollup.findings,
        "reconciliation": rollup.reconciliation,
    }


# --8<-- [start:govern]
def _governed(*, fabric, control_plane, config, ttl, rollup, business,
              materiality, assessment, product_request, store_root):
    """The extension points a deployment supplies, and one call.

    Four seams and nothing else: the projection factory, the debt scorer, the
    product gate, and the TTL figures the class declares. Everything the SDK
    owns is behind :func:`~ccf.products.resolver.build_governed_resolver`.
    """
    from ccf.products.resolver import build_governed_resolver

    def plan_factory(*, required: tuple[str, ...], request: Any) -> Any:
        return proj.ExposureRollupProjection(
            plan_id=f"cp-05.exposure-rollup/{request.subject}",
            required=required,
            threshold=materiality,
            entities=rollup.entities,
            gross_committed=rollup.gross.committed,
            connected_without_exposure=rollup.connected_without_exposure,
            business=business,
        )

    def debt_scorer(*, view: Any, evidence: Any = None) -> Any:
        """cp-05 measures its own debt; the SDK places it on the product."""
        return assessment

    def product_gate(*, candidate: Any, evidence: Any = None) -> str | None:
        """`R-11` — cp-05's own invariant, executed by the fabric."""
        try:
            asm.reconciliation_guard(rollup)
        except AssertionError as violation:
            return str(violation)
        return None

    from ccf.erasure import erasure_index_at  # local: committed docs cite this module by line

    resolver = build_governed_resolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key="product_class",
        request_contract_key="request_contract",
        operator_parameter_keys=(
            "policy.principal-subgraph", "traversal.typed-neighborhood",
        ),
        policy_bundle_key="policy",
        plan_factory=plan_factory,
        debt_scorer=debt_scorer,
        product_gate=product_gate,
        debt_profile_key="debt_profile",
        artifact_store_root=store_root,
        # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
        erasure_index=erasure_index_at(store_root),
        max_ttl_seconds=int(ttl["max_ttl_seconds"]),
        product_ttl_seconds=int(ttl["declared_ttl_seconds"]),
    )
    return resolver(
        tenant=fabric.tenant_id,
        product_class=config["product_class"]["schema_name"],
        version=config["product_class"]["schema_version"],
        perspective=_perspective(config),
        request=product_request,
    )
# --8<-- [end:govern]


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
            # THE DECLARED SET, matching what gate 2 held the candidate to.
            # `lineage.operators_invoked` in the payload additionally names the
            # assembly stages for a human reader; those are not registry
            # operators and gate 2 would refuse them.
            operators_invoked=frozenset(lin["declared_operators"]),
            policy_bundle_versions=frozenset({lin["policy_version"]}),
            # The ledger read is the graph snapshot. Fluree's `t` is TRANSACTION
            # time and `D-IMPL-88` rules it must not back `as_of`; it is recorded
            # BESIDE this boundary, never inside it.
            graph_snapshot_at=asked_at,
        ),
        payload=determination,
    )

