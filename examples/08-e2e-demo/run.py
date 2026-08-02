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

import argparse
import sqlite3
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.factory import AgentFactory
from ccf.agents.prompts import render_instruction
from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    DebtProfile,
    HalfLifeTable,
    declared_artifact_class,
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
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    SKILL_CATALOG_ENTRY,
    SkillCatalog,
    SkillCatalogEntry,
)
from ccf.skills.dispatch import SkillInvocation
from ccf.skills.grants import ApprovalOutcome, GrantLedger, SkillGrant

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


def _require(condition: bool, message: object) -> None:
    """Unconditional verification check (review WR-01).

    Every load-bearing demo check goes through here instead of ``assert``,
    so ``python -O`` / ``PYTHONOPTIMIZE=1`` can never strip the
    verification the README's exit-code-0 promise depends on.
    """
    if not condition:
        raise RuntimeError(f"demo verification failed: {message}")


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38). Attaching UTC at the
    # artifact boundary is the loader's job; the fabric never guesses.
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _ticking_clock(base: datetime) -> Any:
    # Deterministic audit-timestamp source: the base instant is artifact
    # data and each read advances one second. Never a wall-clock read.
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class RefusedSink:
    # The regime declares grant_requires_approval: false — the tier-2 sink
    # must never be consulted; consultation is a hard failure.

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted under an auto regime")


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
    quoted = ", ".join(generator.sql_identifier(name) for name in selected)
    id_sql = generator.sql_identifier(id_column)
    observed_sql = generator.sql_identifier(observed_column)
    table_sql = generator.sql_identifier(table["name"])
    rows: list[dict[str, str]] = []
    with sqlite3.connect(workdir / source["db_file"]) as connection:
        cursor = connection.execute(
            f"SELECT {quoted}, {id_sql}, {observed_sql} "
            f"FROM {table_sql} ORDER BY {id_sql}"
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
        # Guard against zero (division) and negative (sign-inverted
        # tolerance) previous amounts: compare against the magnitude.
        denominator = abs(previous)
        if denominator == 0.0:
            return amount == previous
        return abs(amount - previous) / denominator * 100.0 <= (
            tolerance_percent
        )

    def _walk(start: str, first: tuple[str, str, float, datetime]) -> None:
        # Explicit-stack DFS: path depth is bounded by memory, never by the
        # interpreter recursion limit, so artifact-declared tolerance/span
        # parameters cannot abort the run with RecursionError (WR-04).
        stack: list[list[tuple[str, str, float, datetime]]] = [[first]]
        while stack:
            path = stack.pop()
            last = path[-1]
            node = last[1]
            seen = {step[0] for step in path}
            for edge in adjacency.get(node, ()):
                if edge[3] <= last[3] or edge[3] - path[0][3] > span:
                    continue
                if not _extends(last[2], edge[2]):
                    continue
                if edge[1] == start:
                    if len(path) + 1 >= min_length:
                        found.add(
                            tuple(sorted(step[0] for step in path + [edge]))
                        )
                    continue
                if edge[1] in seen or edge[1] == node:
                    continue
                stack.append(path + [edge])

    for edge in ordered:
        if edge[0] != edge[1]:
            _walk(edge[0], edge)
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


def _governed_detection(
    payload: Mapping[str, Any], arguments: Mapping[str, str]
) -> Mapping[str, str]:
    """The cycle-detection skill body: generic graph mechanism over the
    typed Context Product payload, interpreting ONLY the class, edge-type
    and attribute names the dispatch arguments declare (§6.4). Purely
    algorithmic — no model anywhere on this path (D-10)."""
    party_class = arguments["counterparty_entity_class"]
    transfer_class = arguments["transfer_entity_class"]
    site_link = arguments["site_link_type"]
    registration_link = arguments["registration_link_type"]
    name_attribute = arguments["name_attribute"]
    beneficiary_attribute = arguments["beneficiary_attribute"]

    parties = {
        entity["entity_uri"]: entity["attributes"]
        for entity in payload["entities"]
        if entity["entity_class"] == party_class
    }
    transfers = [
        entity
        for entity in payload["entities"]
        if entity["entity_class"] == transfer_class
    ]
    site_to_parties: dict[str, set[str]] = {}
    transfer_to_site: dict[str, str] = {}
    for edge in payload["relationships"]:
        if edge["relationship_type"] == registration_link:
            site_to_parties.setdefault(edge["object_uri"], set()).add(
                edge["subject_uri"]
            )
        elif edge["relationship_type"] == site_link:
            transfer_to_site[edge["subject_uri"]] = edge["object_uri"]

    # Canonical display names -> party URIs; ambiguous names resolve to
    # nothing rather than to a guess.
    known: dict[str, str] = {}
    ambiguous: set[str] = set()
    for uri in sorted(parties):
        name = parties[uri].get(name_attribute)
        if name is None or name in ambiguous:
            continue
        if name in known and known[name] != uri:
            ambiguous.add(name)
            del known[name]
            continue
        known[name] = uri
    # Wire aliases -> party URIs, via the site the alias's inbound wires
    # deliver to and the counterparty registered at that site — the L2
    # evidence chain, walked over typed edges only.
    for transfer in transfers:
        site = transfer_to_site.get(transfer["entity_uri"])
        candidates = site_to_parties.get(site or "", set())
        if len(candidates) != 1:
            continue
        alias = transfer["attributes"].get(beneficiary_attribute)
        canonical = next(iter(candidates))
        if alias is None or alias in ambiguous:
            continue
        if alias in known and known[alias] != canonical:
            ambiguous.add(alias)
            del known[alias]
            continue
        known[alias] = canonical

    cycles = _run_detection(
        [dict(transfer["attributes"]) for transfer in transfers],
        known=known,
        arguments=arguments,
    )
    first = cycles[0] if cycles else ()
    members = sorted(
        str(parties[uri].get(name_attribute, uri)) for uri in first
    )
    return {
        "cycles_found": str(len(cycles)),
        "cycle_length": str(len(first)),
        "cycle_members": "|".join(members),
    }


def _live_narration(
    *,
    prompt_doc: Any,
    definition: AgentDefinition,
    agent: Agent,
    detection: Mapping[str, str],
    boundary: datetime,
) -> None:
    """Opt-in ``--live`` narration (D-10/D-12): render the prompt artifact
    against the deterministic detection outcome and print the model's
    citation-anchored summary. Prints OUTSIDE the byte-compared narration
    buffer; asserts nothing about model text. The HTTP client import is
    deferred so the deterministic run needs no live dependency wired."""
    import os

    import httpx  # deferred: live-only dependency use

    provider = prompt_doc["live"]["providers"]["ollama"]
    runner = prompt_doc["live"]["runner"]
    base_url = os.environ.get(
        "CCF_OLLAMA_BASE_URL", str(provider["default_base_url"])
    )
    model = os.environ.get(
        "CCF_OLLAMA_MODEL", str(provider["default_model"])
    )
    binding = definition.instruction_bindings[0]
    artifact = agent.instruction_artifact(binding.prompt)
    rendered = render_instruction(
        binding=binding,
        artifact=artifact,
        parameter_values={
            "cycle_members": detection["cycle_members"],
            "as_of": boundary.isoformat(),
        },
    )
    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": rendered}],
            "stream": False,
            "options": {"num_predict": int(runner["max_tokens"])},
        },
        timeout=float(runner["timeout_seconds"]),
    )
    response.raise_for_status()
    print("")
    print(f"--live investigation summary ({model}):")
    print(response.json()["message"]["content"])


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


def main(*, live: bool = False) -> int:
    scenario = _load("scenario.yaml")
    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    halflife = _load("halflife.yaml")
    skills_doc = _load("skills.yaml")
    agent_doc = _load("agent.yaml")
    prompt_doc = _load("prompt.yaml")

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
        _require(shape["row_counts"] == expected_rows(scenario), shape)
        _require(
            shape["checksums"] == scenario["expected"]["checksums"], shape
        )
        _require(
            shape["ring_signature"] == scenario["expected"]["ring_signature"],
            shape,
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
        _require(len(baseline) == expected["baseline_cycles"], baseline)
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
        clock = _ticking_clock(_instant(control["decision"]["clock_base"]))
        registry = ControlPlaneRegistry(clock=clock)
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )
        table = parse_artifact(halflife["half_life_table"], HALF_LIFE_TABLE)
        profile = parse_artifact(halflife["debt_profile"], DEBT_PROFILE)
        _require(isinstance(table, HalfLifeTable), type(table))
        _require(isinstance(profile, DebtProfile), type(profile))
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
            _require(
                len(envelopes) == expected["envelopes_ingested"],
                len(envelopes),
            )
            _require(
                resolved_seeds == expected["resolved_seed_entities"],
                resolved_seeds,
            )
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
            _require(isinstance(gated, ServableProduct), gated)
            _require(
                gated.product.lineage.operators_invoked
                == execution.operators_invoked,
                gated.product.lineage.operators_invoked,
            )
            payload = gated.product.payload
            _require(
                payload["entity_count"] == expected["entity_count"],
                payload["entity_count_by_class"],
            )
            _require(
                payload["entity_count_by_class"]
                == expected["entity_count_by_class"],
                payload["entity_count_by_class"],
            )
            _require(
                payload["relationship_count_by_type"]
                == expected["relationship_count_by_type"],
                payload["relationship_count_by_type"],
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
            _require(0 < retained <= 1, retained)

            # --- Stage 5: AGENT — factory-built, governed skill, the find --
            for reference in agent_doc["referenced_artifacts"].values():
                artifact_class = declared_artifact_class(
                    reference["class_id"]
                )
                declared_artifact = parse_artifact(
                    {
                        "class_id": reference["class_id"],
                        "semver": reference["semver"],
                        "declaration": reference["declaration"],
                    },
                    artifact_class,
                )
                registry.register_typed(
                    reference["key"], declared_artifact, artifact_class
                )
            prompt = parse_artifact(
                prompt_doc["prompt_artifact"], PROMPT_ARTIFACT
            )
            _require(isinstance(prompt, PromptArtifact), type(prompt))
            registry.register_typed(
                prompt_doc["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
            )
            definition = parse_artifact(
                agent_doc["agent_definition"], AGENT_DEFINITION
            )
            _require(
                isinstance(definition, AgentDefinition), type(definition)
            )
            definition_key = agent_doc["keys"]["agent_definition"]
            definition_version = registry.register_versioned(
                definition_key, definition, AGENT_DEFINITION
            )
            _require(
                isinstance(definition_version, str), type(definition_version)
            )
            definition_hash = content_hash(definition)

            catalog = SkillCatalog(registry)
            skill_doc = next(iter(skills_doc["skills"].values()))
            entry = parse_artifact(skill_doc, SKILL_CATALOG_ENTRY)
            _require(isinstance(entry, SkillCatalogEntry), type(entry))
            _require(isinstance(catalog.register(entry), str), entry)
            ledger = GrantLedger(
                control_plane=registry,
                catalog=catalog,
                sink=RefusedSink(),
                clock=clock,
            )
            callables = CallableRegistry()
            callables.register(
                skill_doc["binding"]["callable_ref"],
                lambda call_arguments: _governed_detection(
                    payload, call_arguments
                ),
            )
            agent = AgentFactory(
                control_plane=registry, callable_registry=callables
            ).construct(
                definition_key=definition_key,
                definition_version=definition_version,
                bound_skills=ledger.bound_view(definition_hash),
            )
            _require(isinstance(agent, Agent), type(agent))
            grant = SkillGrant(
                agent_definition_hash=definition_hash, **skills_doc["grant"]
            )
            granted = ledger.request(
                grant,
                definition=definition,
                actor=skills_doc["actors"]["requesting_actor"],
            )
            _require(granted == content_hash(grant), granted)
            in_force = ledger.grant_set_hash(definition_hash)

            _require(
                agent.consume(gated.product, now=now) is gated.product,
                "consumed product is not the served product",
            )
            invocation = agent.invoke_skill(
                skills_doc["grant"]["skill_name"],
                arguments=skills_doc["dispatch"]["arguments"],
            )
            _require(
                isinstance(invocation, SkillInvocation), type(invocation)
            )
            detection = dict(invocation.output)
            _require(
                detection == skills_doc["dispatch"]["expected_output"],
                detection,
            )
            _require(
                int(detection["cycles_found"])
                == expected["governed_cycles"],
                detection,
            )
            _require(
                detection["cycle_members"].split("|")
                == expected["cycle_members"],
                detection,
            )
            _banner(
                "STAGE 5 - AGENT: granted skill over governed context",
                {
                    "agent": f"{definition.name}"
                    f"@{definition.artifact_version}",
                    "archetypes": ", ".join(
                        agent.identity.archetype_composition
                    ),
                    "skill invoked": skills_doc["grant"]["skill_name"],
                    "structured cycles found": detection["cycles_found"],
                    "ring size": detection["cycle_length"],
                    "ring members": detection["cycle_members"],
                    "freshness "
                    + f"({demonstration['observation_type']})": str(retained),
                },
            )

            # --- Stage 6: REPLAY — record, serve, round-trip ----------------
            conditioning = agent.perspective_conditioning(
                principal_id=perspective.principal_id,
                grant_set_hash=in_force,
            )
            record = build_replay_record(
                execution=execution,
                product=gated.product,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(
                        key=keys["policy_bundle"], version=policy_version
                    ),
                ),
                assembly_mode=declared["assembly_mode"],
                recorded_at=now,
                agent_conditioning=conditioning,
            )
            store = FileArtifactStore(root=workdir / "artifacts")
            served = serve(
                product=gated,
                record=record,
                replay_writer=ReplayWriter(
                    store=store,
                    artifact_class=control["artifacts"][
                        "replay_record_class"
                    ],
                ),
            )
            _require(
                store.exists(
                    content_address=served.replay_ref.content_address
                ),
                served.replay_ref.content_address,
            )
            _require(
                served.replay_ref.content_address == content_hash(record),
                served.replay_ref.content_address,
            )
            restored = DecisionReplayRecord.model_validate_json(
                store.get(content_address=served.replay_ref.content_address)
            )
            _require(restored == record, "replay round-trip mismatch")
            _require(
                restored.perspective_conditioning.agent_definition_hash
                == definition_hash,
                restored.perspective_conditioning.agent_definition_hash,
            )
            _require(
                restored.perspective_conditioning.grant_set_hash == in_force,
                restored.perspective_conditioning.grant_set_hash,
            )
            _banner(
                "STAGE 6 - REPLAY: the decision, recorded and served",
                {
                    "replay record": served.replay_ref.content_address[:16]
                    + "...",
                    "dimensions": "fabric snapshot, policy bindings, model"
                    " version, perspective, generation path",
                    "skill-set in force": in_force[:16] + "...",
                },
            )

            # --- narration byte-compare (D-08/D-16) -------------------------
            narration = "\n".join(_NARRATION) + "\n"
            expected_narration = (ARTIFACTS / "expected_output.txt").read_text(
                encoding="utf-8"
            )
            _require(
                narration == expected_narration,
                "staged narration diverged from"
                " artifacts/expected_output.txt",
            )

            print("")
            print("examples/08-e2e-demo: OK")

            if live:
                _live_narration(
                    prompt_doc=prompt_doc,
                    definition=definition,
                    agent=agent,
                    detection=detection,
                    boundary=boundary,
                )
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
    parser = argparse.ArgumentParser(
        description=(
            "End-to-end demo: raw synthetic banking data becomes governed"
            " context and a factory-built agent finds the planted fraud"
            " ring. --live adds LLM narration only; detection is identical"
            " in both modes."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "after the deterministic run completes, render the prompt"
            " artifact and print a live model's investigation summary"
            " (never required, never asserted, never in always-on CI)"
        ),
    )
    sys.exit(main(live=parser.parse_args().live))
