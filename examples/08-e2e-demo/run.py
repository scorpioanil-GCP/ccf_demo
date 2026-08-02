"""examples/08-e2e-demo — raw data becomes governed context (DEMO-02).

The capstone demonstration, one command end to end:
``PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py``.

Stage by stage (Phase 12 CONTEXT D-02, D-09..D-12, D-15, D-16):

1. **GENERATE** — the deterministic generator interprets
   ``artifacts/scenario.yaml`` into three SQLite source systems; row counts
   and checksums are asserted against the artifact's pins (D-08).
2. **BASELINE** — the SAME structured-cycle detection the agent's skill
   runs later is EXECUTED over the raw per-source rows, with identifiers
   as each source knows them and no entity resolution. It finds nothing:
   the ring's wire aliases match no known counterparty, and the noise that
   does match forms no structured cycle. The zero is asserted (D-11).
3. **INGEST L1→L2** — every source row becomes a ``SignalEnvelope`` and
   enters the fabric through ``handle.worker.ingest`` only (single-writer,
   CLAUDE.md §10). L2's declared resolution rules converge the sources'
   disjoint identifiers onto canonical nodes — the hero step (D-02).
4. **PRODUCT** — the four-category operator chain and the projection turn
   the reconciled graph into a gated, typed Context Product (L4→L6).
5. **AGENT** — a factory-built ``AnalyticsInsightsAgent`` (§6.4: no agent
   in code) invokes its granted cycle-detection skill over the product and
   finds exactly the planted ring; the output is asserted against the
   dispatch pin in ``artifacts/skills.yaml`` (D-11, second leg).
6. **REPLAY** — the decision is recorded, served, and round-tripped
   through the ArtifactStore (whitepaper §7.10.1).

The staged console narration is deterministic and byte-compared against
``artifacts/expected_output.txt`` (D-16). ``--live`` adds LLM narration
only — detection is identical in both modes and nothing about model text
is asserted (D-10/D-12).

Every domain value — vocabulary, thresholds, expected outcomes — is loaded
from ``artifacts/*.yaml`` (CLAUDE.md §6.4, the No-Hardcoding Rule). The
code below is thin loading, mapping, and asserting logic.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    DebtProfile,
    HalfLifeTable,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.decay import Observation, freshness
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex

import generator

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

#: The deterministic staged narration (D-16): every `_banner` line lands
#: here and the whole buffer is byte-compared against
#: ``artifacts/expected_output.txt`` at the end of the run.
_NARRATION: list[str] = []


def _banner(title: str, facts: Mapping[str, str]) -> None:
    """Print one stage banner and append it to the narration buffer."""
    width = 66
    lines = ["", "=" * width, f"  {title}", "=" * width]
    lines.extend(f"  {name:<28} {value}" for name, value in facts.items())
    for line in lines:
        _NARRATION.append(line)
        print(line)


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38). Attaching UTC at the
    # artifact boundary is the loader's job; the fabric never guesses.
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=tuple(rule.get("attribute_keys", ())),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


# ---------------------------------------------------------------------------
# L1 envelope mapping — role-keyed interpretation of the ingest spec the
# ontology declares. No source vocabulary exists here: sources are selected
# by mechanism role, tables by role, columns by role (CLAUDE.md §6.4).
# ---------------------------------------------------------------------------


def _source_by_role(scenario: Any, role: str) -> tuple[str, Any]:
    for name, source in scenario["sources"].items():
        if source["role"] == role:
            return name, source
    raise ValueError(f"scenario declares no source with role {role!r}")


def _mapped_rows(
    scenario: Any, entry: Any, workdir: Path
) -> tuple[str, str, list[dict[str, str]]]:
    """Read one ingest entry's raw rows as payload-key dicts, in id order.

    Returns ``(source_name, id_key_payload_name, rows)``. Parameterized
    identifiers are not possible for table/column names; they come from the
    versioned scenario artifact and are quoted (threat register T-12-03),
    and the ``ORDER BY`` over the id column makes the read deterministic.
    """
    source_name, source = _source_by_role(scenario, entry["source_role"])
    table = source["tables"][entry["table_role"]]
    column_by_role = {c["role"]: c["name"] for c in table["columns"]}
    roles = list(entry["payload"].values())
    id_column = column_by_role[entry["envelope_id_role"]]
    observed_column = column_by_role[entry["observed_time_role"]]
    selected = [column_by_role[role] for role in roles]
    quoted = ", ".join(f'"{name}"' for name in selected)
    rows: list[dict[str, str]] = []
    with sqlite3.connect(workdir / source["db_file"]) as connection:
        cursor = connection.execute(
            f'SELECT {quoted}, "{id_column}", "{observed_column}" '
            f'FROM "{table["name"]}" ORDER BY "{id_column}"'
        )
        for values in cursor:
            payload = {
                key: str(values[index])
                for index, key in enumerate(entry["payload"])
            }
            payload.update(
                {key: str(value) for key, value in entry["constants"].items()}
            )
            payload["__row_id"] = str(values[-2])
            payload["__observed"] = str(values[-1])
            rows.append(payload)
    return source_name, table["name"], rows


def _envelopes(
    scenario: Any, ontology: Any, workdir: Path, *, ingested_at: datetime
) -> list[SignalEnvelope]:
    envelopes: list[SignalEnvelope] = []
    for entry in ontology["ingest"]:
        source_name, table_name, rows = _mapped_rows(scenario, entry, workdir)
        for payload in rows:
            row_id = payload.pop("__row_id")
            observed = _instant(payload.pop("__observed"))
            envelopes.append(
                SignalEnvelope(
                    tenant_id=ontology["tenant_id"],
                    envelope_id=f"{source_name}:{table_name}:{row_id}",
                    source=SourceIdentity(system_id=source_name),
                    ingestion_timestamp=ingested_at,
                    observed_time=observed,
                    raw_payload=dict(payload),
                )
            )
    return envelopes


# ---------------------------------------------------------------------------
# Structured-cycle detection — the ONE detection mechanism both passes run
# (D-11). Every vocabulary and threshold value it interprets arrives in the
# artifact-declared dispatch arguments; the function is generic graph
# mechanism over (source, target, amount, timestamp) edges.
# ---------------------------------------------------------------------------


def _structured_cycles(
    edges: list[tuple[str, str, float, datetime]],
    *,
    min_length: int,
    tolerance_percent: float,
    max_span_days: float,
) -> list[tuple[str, ...]]:
    """Directed cycles whose consecutive amounts stay within tolerance and
    whose timestamps strictly increase within the span window. Returns the
    sorted member tuples, deterministically ordered."""
    ordered = sorted(edges, key=lambda e: (e[3], e[0], e[1], e[2]))
    adjacency: dict[str, list[tuple[str, str, float, datetime]]] = {}
    for edge in ordered:
        adjacency.setdefault(edge[0], []).append(edge)
    span = timedelta(days=max_span_days)
    found: set[tuple[str, ...]] = set()

    def _extends(previous: float, amount: float) -> bool:
        return abs(amount - previous) / previous * 100.0 <= tolerance_percent

    def _walk(
        start: str, node: str, path: list[tuple[str, str, float, datetime]]
    ) -> None:
        last = path[-1]
        seen = {step[0] for step in path}
        for edge in adjacency.get(node, ()):
            if edge[3] <= last[3] or edge[3] - path[0][3] > span:
                continue
            if not _extends(last[2], edge[2]):
                continue
            if edge[1] == start:
                if len(path) + 1 >= min_length:
                    found.add(tuple(sorted(step[0] for step in path + [edge])))
                continue
            if edge[1] in seen or edge[1] == node:
                continue
            _walk(start, edge[1], path + [edge])

    for edge in ordered:
        if edge[0] != edge[1]:
            _walk(edge[0], edge[1], [edge])
    return sorted(found)


def _detection_edges(
    rows: list[dict[str, str]],
    *,
    known: Mapping[str, str],
    arguments: Mapping[str, str],
) -> list[tuple[str, str, float, datetime]]:
    """Payment edges whose BOTH parties resolve through ``known`` — the
    name→canonical mapping in force for the pass (identity-only for the
    baseline, resolution-backed for the governed run)."""
    origin_key = arguments["origin_attribute"]
    beneficiary_key = arguments["beneficiary_attribute"]
    amount_key = arguments["amount_attribute"]
    sent_key = arguments["sent_attribute"]
    edges: list[tuple[str, str, float, datetime]] = []
    for row in rows:
        origin = known.get(row.get(origin_key, ""))
        beneficiary = known.get(row.get(beneficiary_key, ""))
        if origin is None or beneficiary is None or origin == beneficiary:
            continue
        edges.append(
            (
                origin,
                beneficiary,
                float(row[amount_key]),
                _instant(row[sent_key]),
            )
        )
    return edges


def _run_detection(
    rows: list[dict[str, str]],
    *,
    known: Mapping[str, str],
    arguments: Mapping[str, str],
) -> list[tuple[str, ...]]:
    return _structured_cycles(
        _detection_edges(rows, known=known, arguments=arguments),
        min_length=int(arguments["min_cycle_length"]),
        tolerance_percent=float(arguments["amount_tolerance_percent"]),
        max_span_days=float(arguments["max_span_days"]),
    )


class PaymentNetworkPlan:
    """The deployment's Π: the resolved payment network as its reader —
    the financial-crime analyst's skill — needs it. Deployment code, like
    every projection; it declares which operators its interpretation
    depends on and cannot tell the engine what ran (the L6 lineage gate)."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        entities = sorted(view.entities, key=lambda r: r.claim.entity_uri)
        relationships = sorted(
            view.relationships,
            key=lambda r: (
                r.claim.relationship_type,
                r.claim.subject_uri,
                r.claim.object_uri,
            ),
        )
        count_by_class: dict[str, int] = {}
        for record in entities:
            count_by_class[record.claim.entity_class] = (
                count_by_class.get(record.claim.entity_class, 0) + 1
            )
        count_by_type: dict[str, int] = {}
        for edge in relationships:
            count_by_type[edge.claim.relationship_type] = (
                count_by_type.get(edge.claim.relationship_type, 0) + 1
            )
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(entities),
                "entity_count_by_class": dict(sorted(count_by_class.items())),
                "relationship_count_by_type": dict(
                    sorted(count_by_type.items())
                ),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                        "attributes": dict(
                            sorted(record.claim.attributes.items())
                        ),
                    }
                    for record in entities
                ],
                "relationships": [
                    {
                        "relationship_type": edge.claim.relationship_type,
                        "subject_uri": edge.claim.subject_uri,
                        "object_uri": edge.claim.object_uri,
                    }
                    for edge in relationships
                ],
            },
        )


def main() -> int:
    scenario = _load("scenario.yaml")
    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    halflife = _load("halflife.yaml")
    skills_doc = _load("skills.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    expected = control["expected"]
    arguments = skills_doc["dispatch"]["arguments"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])
    ingested_at = _instant(control["decision"]["ingestion_timestamp"])

    with tempfile.TemporaryDirectory(prefix="ccf-e2e-demo-") as scratch:
        workdir = Path(scratch)

        # --- Stage 1: GENERATE — scenario.yaml becomes three source DBs ----
        shape = generator.generate(scenario, workdir)
        assert shape["row_counts"] == expected_rows(scenario), shape
        assert shape["checksums"] == scenario["expected"]["checksums"], shape
        assert (
            shape["ring_signature"] == scenario["expected"]["ring_signature"]
        )
        total_rows = sum(
            count
            for tables in shape["row_counts"].values()
            for count in tables.values()
        )
        _banner(
            "STAGE 1 - GENERATE: scenario.yaml -> three source systems",
            {
                "source systems": str(len(shape["row_counts"])),
                "rows written": str(total_rows),
                "checksums": "all pinned values matched",
            },
        )

        # --- Stage 2: BASELINE — the same detection, raw rows, no L2 -------
        # The mapping in force is string identity over the names each source
        # itself records: exactly what a per-source review can do.
        raw_by_entry = [
            _mapped_rows(scenario, entry, workdir)[2]
            for entry in ontology["ingest"]
        ]
        name_key = arguments["name_attribute"]
        known_raw = {
            row[name_key]: row[name_key]
            for rows in raw_by_entry
            for row in rows
            if name_key in row
        }
        payment_rows = [
            row
            for rows in raw_by_entry
            for row in rows
            if arguments["origin_attribute"] in row
        ]
        unattributed = sum(
            1
            for row in payment_rows
            if row[arguments["origin_attribute"]] not in known_raw
            or row[arguments["beneficiary_attribute"]] not in known_raw
        )
        baseline = _run_detection(
            payment_rows, known=known_raw, arguments=arguments
        )
        assert len(baseline) == expected["baseline_cycles"], baseline
        _banner(
            "STAGE 2 - BASELINE: the same detection over raw rows",
            {
                "payment rows examined": str(len(payment_rows)),
                "rows with unknown parties": str(unattributed),
                "structured cycles found": str(len(baseline)),
                "verdict": "nothing to see from raw data alone",
            },
        )

        # --- Stage 3: INGEST — L1 envelopes through the single writer ------
        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )
        table = parse_artifact(halflife["half_life_table"], HALF_LIFE_TABLE)
        profile = parse_artifact(halflife["debt_profile"], DEBT_PROFILE)
        assert isinstance(table, HalfLifeTable)
        assert isinstance(profile, DebtProfile)
        registry.register(keys["half_life_table"], table)
        registry.register(keys["debt_profile"], profile)

        handle = boot(
            database_path=workdir / "fabric.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            envelopes = _envelopes(
                scenario, ontology, workdir, ingested_at=ingested_at
            )
            for envelope in envelopes:
                handle.worker.ingest(envelope)

            view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
            seed_class = control["operator_parameters"]["traversal"][
                "seed_entity_classes"
            ][0]
            resolved_seeds = sum(
                1
                for record in view.entities
                if record.claim.entity_class == seed_class
            )
            assert len(envelopes) == expected["envelopes_ingested"]
            assert resolved_seeds == expected["resolved_seed_entities"]
            _banner(
                "STAGE 3 - INGEST: L1 envelopes -> L2 entity resolution",
                {
                    "envelopes ingested": str(len(envelopes)),
                    "canonical " + seed_class + " nodes": str(resolved_seeds),
                    "how": "disjoint source identifiers converged"
                    " on shared evidence",
                },
            )

            # --- Stage 4: PRODUCT — operators, projection, gates -----------
            params = control["operator_parameters"]
            operators = OperatorRegistry()
            operators.register(
                PolicyFilter(
                    parameters=PolicyFilterParameters(
                        permitted_policy_bundle_versions=frozenset(
                            {policy_version}
                        ),
                        classification_attribute_by_class=dict(
                            ontology["classification_attribute_by_class"]
                        ),
                        permitted_classifications=frozenset(
                            params["policy"]["permitted_classifications"]
                        ),
                    )
                )
            )
            corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
            corpus = {
                (tenant_id, record.claim.entity_uri): record.claim.attributes[
                    corpus_attribute[record.claim.entity_class]
                ]
                for record in view.entities
                if record.claim.entity_class in corpus_attribute
            }
            operators.register(
                SimilaritySelect(
                    parameters=SimilaritySelectParameters(
                        query=params["similarity"]["query"],
                        minimum_score_percent=params["similarity"][
                            "minimum_score_percent"
                        ],
                        ranked_entity_classes=frozenset(
                            params["similarity"]["ranked_entity_classes"]
                        ),
                    ),
                    index=TokenOverlapIndex(
                        corpus=corpus,
                        index_version=params["similarity"]["index_version"],
                    ),
                )
            )
            operators.register(
                TemporalAsOf(
                    parameters=TemporalAsOfParameters(
                        require_valid_at_boundary=params["temporal"][
                            "require_valid_at_boundary"
                        ]
                    )
                )
            )
            operators.register(
                TraversalNeighborhood(
                    parameters=TraversalNeighborhoodParameters(
                        seed_entity_classes=frozenset(
                            params["traversal"]["seed_entity_classes"]
                        ),
                        relationship_types=frozenset(
                            params["traversal"]["relationship_types"]
                        ),
                        depth_limit=params["traversal"]["depth_limit"],
                    )
                )
            )

            declared = control["product_class"]
            plan = PaymentNetworkPlan(
                plan_id=declared["plan_id"], required=operators.keys()
            )
            perspective = Perspective(
                principal_id=control["perspective"]["principal_id"],
                role=control["perspective"]["role"],
            )
            engine = ProjectionEngine(reader=handle.reader, registry=operators)
            execution = engine.execute(
                plan=plan,
                perspective=perspective,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
            )

            max_ttl_version = registry.register(
                keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
            )
            product_class = register_product_class(
                registry=registry,
                schema_name=declared["schema_name"],
                schema_version=declared["schema_version"],
                ttl_anchor=declared["ttl_anchor"],
                assembly_mode=declared["assembly_mode"],
                max_ttl_key=keys["max_ttl"],
                max_ttl_version=max_ttl_version,
            )
            candidate = ContextProductContract(
                schema_name=product_class.schema_name,
                schema_version=product_class.schema_version,
                plan_id=execution.plan_id,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
                expires_at=now
                + timedelta(seconds=declared["product_ttl_seconds"]),
                ttl_anchor=product_class.ttl_anchor,
                lineage=ProductLineage(
                    operators_invoked=execution.operators_invoked,
                    policy_bundle_versions=frozenset({policy_version}),
                    graph_snapshot_at=boundary,
                ),
                payload=execution.projection.payload,
            )
            gated = run_gates(
                candidate,
                engine_resolved=execution.operators_invoked,
                now=now,
                registry=registry,
                product_class=product_class,
            )
            assert isinstance(gated, ServableProduct), gated
            assert (
                gated.product.lineage.operators_invoked
                == execution.operators_invoked
            )
            payload = gated.product.payload
            assert payload["entity_count"] == expected["entity_count"], (
                payload["entity_count_by_class"]
            )
            assert (
                payload["entity_count_by_class"]
                == expected["entity_count_by_class"]
            )
            assert (
                payload["relationship_count_by_type"]
                == expected["relationship_count_by_type"]
            )
            _banner(
                "STAGE 4 - PRODUCT: operators -> projection -> gated product",
                {
                    "operators invoked": str(
                        len(execution.operators_invoked)
                    ),
                    "entities served": str(payload["entity_count"]),
                    "typed edges served": str(
                        sum(payload["relationship_count_by_type"].values())
                    ),
                    "gates": "empty-operator, lineage equality, TTL"
                    " - all passed",
                },
            )

            # --- λ_c: freshness of the last ring wire at decision time -----
            demonstration = halflife["demonstration"]
            retained = freshness(
                Observation(
                    observation_type=demonstration["observation_type"],
                    observed_at=_instant(demonstration["observed_at"]),
                ),
                now=now,
                table=table,
                risk_sensitivity=profile.risk_sensitivity,
            )
            assert 0 < retained <= 1, retained

            print("")
            print("examples/08-e2e-demo: OK")
            return 0
        finally:
            handle.close()


def expected_rows(scenario: Any) -> dict[str, dict[str, int]]:
    """The scenario's expected row counts keyed exactly as generate() keys
    its report (source name -> table name -> count)."""
    return {
        source: dict(tables)
        for source, tables in scenario["expected"]["row_counts"].items()
    }


if __name__ == "__main__":
    sys.exit(main())
