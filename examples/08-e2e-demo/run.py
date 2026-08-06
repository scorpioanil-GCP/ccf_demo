"""examples/08-e2e-demo — raw data becomes governed context (DEMO-02).

The capstone demonstration, one command end to end:
``PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`` (or
``make example-08``).

Stage by stage (Phase 12 CONTEXT D-02, D-09..D-12, D-15, D-16):

1. **GENERATE** — the deterministic generator interprets
   ``artifacts/scenario.yaml`` into three SQLite source systems.
2. **BASELINE** — the SAME structured-cycle detection the agent's skill runs
   later is EXECUTED over the raw per-source rows, with identifiers as each
   source knows them and no entity resolution. It finds nothing: the ring's
   wire aliases match no known counterparty, and the noise that does match
   forms no structured cycle (D-11).
3. **INGEST L1→L2** — every source row becomes a ``SignalEnvelope`` and enters
   the fabric through ``handle.worker.ingest`` only (single-writer, CLAUDE.md
   §10). L2's declared resolution rules converge the sources' disjoint
   identifiers onto canonical nodes — the hero step (D-02).
4. **PRODUCT** — the four-category operator chain and the projection turn the
   reconciled graph into a gated, typed Context Product (L4→L6).
5. **AGENT** — a factory-built ``AnalyticsInsightsAgent`` (§6.4: no agent in
   code) invokes its granted cycle-detection skill over the product and finds
   exactly the planted ring.
6. **REPLAY** — the decision is recorded, served, and round-tripped through the
   ArtifactStore (whitepaper §7.10.1).

**This file no longer carries its own guarantee.** It asserts nothing: its
checks — including the byte-comparison of the staged narration against
``artifacts/expected_output.txt`` (D-16), which is this demo's *whole*
correctness claim — live in ``tests/examples/test_e2e_demo_output.py``, where a
runner can actually fail a build (D-09). ``make example-08`` running clean means
the spine executed; ``pytest`` is what says it was right. It still prints,
because the narration is the demonstration's product rather than a debug aid.

``--live`` adds LLM narration only — detection is identical in both modes and
nothing about model text is asserted (D-10/D-12).

Every domain value — vocabulary, thresholds, expected outcomes — is loaded from
``artifacts/*.yaml`` and the fabric's share of them is enumerated by
``artifacts/manifest.yaml`` (CLAUDE.md §6.4, the No-Hardcoding Rule). Deleting
the artifacts leaves this file with nothing meaningful to run.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.agents.prompts import render_instruction
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    declared_artifact_class,
    load_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import (
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphView
from ccf.halflife.decay import Observation, freshness
from ccf.operators.base import OperatorOutput
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
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
MANIFEST = ARTIFACTS / "manifest.yaml"


def _banner(
    narration: list[str], title: str, facts: Mapping[str, str]
) -> None:
    """Print one stage banner and append it to the narration buffer.

    The buffer is the demo's deliverable: ``tests/examples/`` byte-compares the
    joined lines against ``artifacts/expected_output.txt`` (D-16). It is passed
    in rather than held at module scope so that two runs in one process — which
    is exactly what a test session does — cannot silently concatenate.
    """
    width = 66
    lines = ["", "=" * width, f"  {title}", "=" * width]
    lines.extend(f"  {name:<28} {value}" for name, value in facts.items())
    for line in lines:
        narration.append(line)
        print(line)


def _ticking_clock(base: datetime) -> Any:
    """Deterministic audit-timestamp source, seeded from artifact data.

    Each read advances one second. Never a wall-clock read: an audit plane whose
    timestamps come from the machine is one whose records differ between two
    identical runs.
    """
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class RefusedSink:
    """The tier-2 approval sink, which must never be consulted.

    ``agent-policy-regime.yaml`` declares ``grant_requires_approval: false``, so
    consulting a human is not merely unnecessary here — it would mean the
    governance tier was resolved wrongly. Raising rather than returning an
    outcome is what turns "the auto regime did not silently escalate" into
    something the run executes rather than assumes.
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted under an auto regime")


# ---------------------------------------------------------------------------
# L1 envelope mapping — role-keyed interpretation of the ingest spec.
#
# This example ingests from three LIVE SQLite source systems the generator
# writes, not from a `ccf.signal-batch`: the events do not exist until the run
# creates them, so there is no static batch document to name and this
# translation is a genuine demonstration concern rather than mechanical
# marshalling the SDK could absorb. What IS declared is the mapping
# (`artifacts/ingest-spec.yaml`): sources are selected by mechanism role,
# tables by role, columns by role, so no source vocabulary exists here
# (CLAUDE.md §6.4).
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

    Returns ``(source_name, table_name, rows)``. Parameterized identifiers are
    not possible for table/column names; they come from the versioned scenario
    artifact and are quoted (threat register T-12-03), and the ``ORDER BY`` over
    the id column makes the read deterministic.
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


# ---------------------------------------------------------------------------
# Structured-cycle detection — the ONE detection mechanism both passes run
# (D-11). Every vocabulary and threshold value it interprets arrives in the
# artifact-declared dispatch arguments; the function is generic graph mechanism
# over (source, target, amount, timestamp) edges.
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
        # Guard against zero (division) and negative (sign-inverted tolerance)
        # previous amounts: compare against the magnitude.
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
                datetime.fromisoformat(row[sent_key]),
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
    """The cycle-detection skill body: generic graph mechanism over the typed
    Context Product payload, interpreting ONLY the class, edge-type and
    attribute names the dispatch arguments declare (§6.4). Purely algorithmic —
    no model anywhere on this path (D-10)."""
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

    # Canonical display names -> party URIs; ambiguous names resolve to nothing
    # rather than to a guess.
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
    # Wire aliases -> party URIs, via the site the alias's inbound wires deliver
    # to and the counterparty registered at that site — the L2 evidence chain,
    # walked over typed edges only.
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
    live_config: Mapping[str, Any],
    definition: AgentDefinition,
    agent: Agent,
    detection: Mapping[str, str],
    boundary: datetime,
) -> None:
    """Opt-in ``--live`` narration (D-10/D-12): render the prompt artifact
    against the deterministic detection outcome and print the model's
    citation-anchored summary. Prints OUTSIDE the byte-compared narration
    buffer; asserts nothing about model text. The HTTP client import is deferred
    so the deterministic run needs no live dependency wired."""
    import os

    import httpx  # deferred: live-only dependency use

    provider = live_config["providers"]["ollama"]
    runner = live_config["runner"]
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
    """The deployment's Π: the resolved payment network as its reader — the
    financial-crime analyst's skill — needs it.

    A projection is deployment code, and never a rewrite target (whitepaper
    §7.5). It declares which operators its interpretation depends on and
    interprets their output; it does not run them and cannot tell the engine
    what ran, which is what leaves the L6 lineage gate something real to check.

    ``required`` is passed in from ``artifacts/projection-requirements.yaml``
    (``ccf.projection-requirements``) — the projection's OWN document, not the
    product class's and not the operator registry's keys. Under design E2
    (``docs/DECISIONS.md`` D-IMPL-86 and its correction of 2026-08-05) the two
    operator sets a deployment authors are separate documents:
    ``product-class.yaml``'s ``required_operator_keys`` is the Control Plane
    **claim** that fills the product's lineage, and this one is what the plan
    requires. ``refuse_operator_set_divergence`` binds them, between plan
    construction and ``ProjectionEngine.execute``, and that is where
    **authorable drift** fails.

    Feeding ``required`` from the product-class declaration instead would not be
    a second source at all: the declaration would reach the engine's
    ``operators_invoked`` through five pure transforms with no branch, so the
    two would be identical by construction and nothing an author could write
    would separate them.
    """

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


@dataclass(frozen=True)
class DemoResult:
    """What one run of the demo produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_e2e_demo_output.py`` can hold the assertions where a
    test runner will actually run them (D-09).
    """

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    scenario: Mapping[str, Any]
    generated: Mapping[str, Any]
    baseline_cycles: tuple[tuple[str, ...], ...]
    payment_rows: int
    unattributed_rows: int
    envelopes_ingested: int
    resolved_seed_entities: int
    product: ContextProductContract
    operators_invoked: tuple[str, ...]
    detection: Mapping[str, str]
    agent: Agent
    definition: AgentDefinition
    definition_hash: str
    granted_hash: str
    grant_set_hash: str
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore
    retained_freshness: Decimal
    narration: str
    expected_narration: str


def expected_rows(scenario: Any) -> dict[str, dict[str, int]]:
    """The scenario's expected row counts keyed exactly as generate() keys its
    report (source name -> table name -> count)."""
    return {
        source: dict(tables)
        for source, tables in scenario["expected"]["row_counts"].items()
    }


def run(*, root: Path, live: bool = False) -> DemoResult:
    """Run the whole demonstration once against ``root`` as its scratch dir."""
    narration: list[str] = []

    # `scenario.yaml` is the GENERATOR's input, not a fabric artifact: it
    # describes the synthetic world, which exists before any fabric does, and it
    # is deliberately outside the deployment manifest. Plain YAML is right here.
    scenario = yaml.safe_load((ARTIFACTS / "scenario.yaml").read_text("utf-8"))

    # The audit clock must exist before the FIRST registration, and the first
    # registration happens inside `load_and_boot` — so the one instant that
    # seeds it is read here, through the SDK's own artifact loader, from the
    # very document the manifest names as `decision`. Everything after boot
    # reads that artifact off `booted.artifacts`; this is the single ordering
    # constraint the one-call boot cannot absorb.
    decision_document = (ARTIFACTS / "decision.yaml").read_text("utf-8")
    decision = cast(
        DeclaredArtifact,
        load_artifact(
            decision_document,
            # The class the document declares of itself. Not a literal here:
            # the manifest names the same class independently and
            # `load_and_boot` validates the document against it a second time,
            # so the two-independent-statements property is not lost by
            # reading it from the document at this one point.
            declared_artifact_class(
                yaml.safe_load(decision_document)["class_id"]
            ),
        ),
    )
    clock = _ticking_clock(
        datetime.fromisoformat(decision.declaration["clock_base"])
    )
    registry = ControlPlaneRegistry(clock=clock)

    # --- Stage 1: GENERATE — scenario.yaml becomes three source DBs ---------
    generated = generator.generate(scenario, root)
    total_rows = sum(
        count
        for tables in generated["row_counts"].values()
        for count in tables.values()
    )
    _banner(
        narration,
        "STAGE 1 - GENERATE: scenario.yaml -> three source systems",
        {
            "source systems": str(len(generated["row_counts"])),
            "rows written": str(total_rows),
            "checksums": "all pinned values matched",
        },
    )

    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(root / "fabric.sqlite3")
    )
    try:
        # Each artifact comes back under its own manifest key, already validated
        # against the class the manifest declared for it — so these casts
        # restate what `load_and_boot` already enforced.
        ingest_spec = cast(DeclaredArtifact, booted.artifacts["ingest-spec"])
        governance = cast(
            DeclaredArtifact, booted.artifacts["product-governance"]
        )
        declared = cast(
            ProductClassDeclaration, booted.artifacts["product-class"]
        )
        requirements = cast(
            ProjectionRequirements,
            booted.artifacts["projection-requirements"],
        )
        perspective = cast(
            PerspectiveArtifact, booted.artifacts["perspective"]
        )
        expected = cast(DeclaredArtifact, booted.artifacts["expected"])

        boundary = datetime.fromisoformat(
            decision.declaration["temporal_boundary"]
        )
        now = datetime.fromisoformat(decision.declaration["now"])
        ingested_at = datetime.fromisoformat(
            decision.declaration["ingestion_timestamp"]
        )

        # The grant request, the dispatch and the filing keys all come back off
        # the manifest like everything else. The three AUTHOR-VERSIONED
        # documents do not — see below.
        skill_dispatch = cast(
            DeclaredArtifact, booted.artifacts["skill-dispatch"]
        ).declaration
        registration = cast(
            DeclaredArtifact, booted.artifacts["agent-registration"]
        ).declaration
        arguments = skill_dispatch["dispatch"]["arguments"]

        # --- Stage 2: BASELINE — the same detection, raw rows, no L2 --------
        # The mapping in force is string identity over the names each source
        # itself records: exactly what a per-source review can do.
        raw_by_entry = [
            _mapped_rows(scenario, entry, root)[2]
            for entry in ingest_spec.declaration["ingest"]
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
        _banner(
            narration,
            "STAGE 2 - BASELINE: the same detection over raw rows",
            {
                "payment rows examined": str(len(payment_rows)),
                "rows with unknown parties": str(unattributed),
                "structured cycles found": str(len(baseline)),
                "verdict": "nothing to see from raw data alone",
            },
        )

        # --- Stage 3: INGEST — L1 envelopes through the single writer -------
        envelopes: list[SignalEnvelope] = []
        for entry in ingest_spec.declaration["ingest"]:
            source_name, table_name, rows = _mapped_rows(scenario, entry, root)
            for payload in rows:
                row_id = payload.pop("__row_id")
                observed = datetime.fromisoformat(payload.pop("__observed"))
                envelopes.append(
                    SignalEnvelope(
                        tenant_id=booted.tenant_id,
                        envelope_id=f"{source_name}:{table_name}:{row_id}",
                        source=SourceIdentity(system_id=source_name),
                        ingestion_timestamp=ingested_at,
                        observed_time=observed,
                        raw_payload=dict(payload),
                    )
                )
        for envelope in envelopes:
            booted.handle.worker.ingest(envelope)

        # The graph view at the temporal boundary this deployment named.
        view = booted.handle.reader.as_of(
            tenant_id=booted.tenant_id, at=boundary
        )
        # The banner names the seeded class. Sorted rather than "first": the
        # artifact's set is unordered, and a banner whose text depended on set
        # iteration order would break the byte-comparison at random.
        traversal = cast(Any, booted.artifacts["traversal"])
        seed_class = sorted(traversal.seed_entity_classes)[0]
        resolved_seeds = sum(
            1
            for record in view.entities
            if record.claim.entity_class == seed_class
        )
        _banner(
            narration,
            "STAGE 3 - INGEST: L1 envelopes -> L2 entity resolution",
            {
                "envelopes ingested": str(len(envelopes)),
                "canonical " + seed_class + " nodes": str(resolved_seeds),
                "how": "disjoint source identifiers converged"
                " on shared evidence",
            },
        )

        # --- Stage 4: PRODUCT — operators, projection, gates ----------------
        # The operator-parameters mapping, assembled by naming this deployment's
        # OWN manifest keys. Deliberately not an isinstance filter or a class-id
        # match: those are type introspection, and copied across nine examples
        # they would be a new duplication class.
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
            for key in ("traversal", "temporal", "policy", "similarity")
        }
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key="policy-bundle",
            similarity_index_version=governance.declaration[
                "similarity_index_version"
            ],
        )
        # The plan's `required` comes from the projection's OWN artifact — never
        # from the operator registry's keys, and never from the product class,
        # which is the claim rather than the plan's input.
        #
        # The plan is a named local so the binder has a statement to occupy: the
        # refusal belongs BETWEEN plan construction and `execute` (D-IMPL-86's
        # correction of 2026-08-05), and a plan built inline as `execute`'s own
        # argument leaves no such line. Edit either authored document alone and
        # this demo stops here, before a product is assembled from a set the
        # deployment's own claim contradicts.
        plan = PaymentNetworkPlan(
            plan_id=governance.declaration["plan_id"],
            required=requirements.required_operator_keys,
        )
        refuse_operator_set_divergence(declared=declared, plan=plan)
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
        )

        # L6 — and this cluster stays in adopter code deliberately.
        #
        # Gate 3 compares the class's TTL CEILING against this product's own
        # `expires_at`. That is only a check while the two are independently
        # authored. Registering the MaxTTL value here is what MINTS
        # `max_ttl_version` — the pin is a content hash of what was registered,
        # which is why the product-class artifact cannot declare it. A helper
        # that minted the pin and stamped the product would be comparing a value
        # against itself, so the SDK ships no such helper and these lines
        # survive the ergonomics phase on purpose. Do not remove them.
        max_ttl_version = registry.register(
            declared.max_ttl_key,
            MaxTTL(seconds=governance.declaration["max_ttl_seconds"]),
        )
        product_class = register_product_class(
            registry=registry,
            schema_name=declared.schema_name,
            schema_version=declared.schema_version,
            ttl_anchor=declared.ttl_anchor,
            assembly_mode=declared.assembly_mode,
            max_ttl_key=declared.max_ttl_key,
            max_ttl_version=max_ttl_version,
        )

        # The lineage the product CLAIMS, and the gates.
        #
        # The claim is the product class's `required_operator_keys` — the
        # Control Plane's authored statement of what this product's assembly
        # depends on. It is never `execution.operators_invoked`: filling the
        # claim from the engine's own report would make Gate 2 compare a value
        # against itself.
        #
        # What Gate 2 then verifies is ASSEMBLY-PATH INTEGRITY: that the product
        # served was assembled by the path the deployment claimed. The engine is
        # a faithful transcriber of the plan rather than an independent witness
        # of it — it builds its invoked set and its steps in one loop over the
        # same operator plan — so the gate catches an assembly that departed
        # from the plan, not a claim that was wrong to begin with. Authorable
        # drift fails upstream, at `refuse_operator_set_divergence`.
        policy_version = booted.pins.version_for("policy-bundle")
        candidate = ContextProductContract(
            schema_name=product_class.schema_name,
            schema_version=product_class.schema_version,
            plan_id=execution.plan_id,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
            expires_at=now
            + timedelta(
                seconds=governance.declaration["product_ttl_seconds"]
            ),
            ttl_anchor=product_class.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(declared.required_operator_keys),
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=boundary,
            ),
            payload=execution.projection.payload,
        )
        # A refusal is not a thing to proceed past: `ServableProduct` is not
        # constructible outside `run_gates`, so holding one IS the evidence the
        # gates ran (INV-CH7-52).
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=now,
            registry=registry,
            product_class=product_class,
        ):
            case ServableProduct() as gated:
                pass
            case refusal:
                raise RuntimeError(
                    f"the three validation gates refused this product:"
                    f" {refusal}"
                )
        payload = gated.product.payload
        _banner(
            narration,
            "STAGE 4 - PRODUCT: operators -> projection -> gated product",
            {
                "operators invoked": str(len(execution.operators_invoked)),
                "entities served": str(payload["entity_count"]),
                "typed edges served": str(
                    sum(payload["relationship_count_by_type"].values())
                ),
                "gates": "empty-operator, lineage equality, TTL"
                " - all passed",
            },
        )

        # λ_c: the retained decision-relevance of the last ring wire at the
        # decision instant (whitepaper §7.7).
        table = cast(HalfLifeTable, booted.artifacts["half-life-table"])
        profile = cast(Any, booted.artifacts["debt-profile"])
        observation = Observation.model_validate(
            decision.declaration["freshness_demonstration"]
        )
        retained = freshness(
            observation,
            now=now,
            table=table,
            risk_sensitivity=profile.risk_sensitivity,
        )

        # --- Stage 5: AGENT — factory-built, governed skill, the find -------
        # The agent's axis-4 and axis-5 documents are already registered: the
        # manifest named them under the very keys the definition's
        # versioned-URI refs resolve against, so no registration loop is needed
        # here any more.
        #
        # These three ARE loaded here rather than by the manifest, and the
        # reason is governance rather than convenience. `ccf.agent-definition`,
        # `ccf.prompt-artifact` and `ccf.skill-catalog-entry` are
        # AUTHOR-VERSIONED: they carry the author's own `artifact_version`, and
        # the definition registers through `register_versioned`, which holds
        # that claim against the document's content identity (the D-05 bump
        # check). `load_and_boot` registers through `register_typed`, which does
        # not run it — so the SDK keeps these classes out of
        # `SDK_ARTIFACT_CLASSES` and a manifest entry naming one would parse
        # fine while silently dropping the governance the class exists to carry.
        # They still validate against their real contracts here, and they still
        # carry real `$schema` headers (plan 15-14's author-versioned set).
        prompt = load_artifact(
            (ARTIFACTS / "prompt-artifact.yaml").read_text("utf-8"),
            PROMPT_ARTIFACT,
        )
        registry.register_typed(
            registration["prompt_artifact_key"], prompt, PROMPT_ARTIFACT
        )
        definition = cast(
            AgentDefinition,
            load_artifact(
                (ARTIFACTS / "agent-definition.yaml").read_text("utf-8"),
                AGENT_DEFINITION,
            ),
        )
        definition_key = registration["agent_definition_key"]
        definition_version = registry.register_versioned(
            definition_key, definition, AGENT_DEFINITION
        )
        definition_hash = content_hash(definition)

        catalog = SkillCatalog(registry)
        entry = cast(
            SkillCatalogEntry,
            load_artifact(
                (ARTIFACTS / "skill-catalog-entry.yaml").read_text("utf-8"),
                SKILL_CATALOG_ENTRY,
            ),
        )
        catalog.register(entry)
        ledger = GrantLedger(
            control_plane=registry,
            catalog=catalog,
            sink=RefusedSink(),
            clock=clock,
        )
        callables = CallableRegistry()
        callables.register(
            entry.binding.callable_ref,
            lambda call_arguments: _governed_detection(payload, call_arguments),
        )
        agent = AgentFactory(
            control_plane=registry, callable_registry=callables
        ).construct(
            definition_key=definition_key,
            definition_version=definition_version,
            bound_skills=ledger.bound_view(definition_hash),
        )
        grant = SkillGrant(
            agent_definition_hash=definition_hash,
            **skill_dispatch["grant_request"],
        )
        granted = ledger.request(
            grant,
            definition=definition,
            actor=skill_dispatch["requesting_actor"],
        )
        in_force = ledger.grant_set_hash(definition_hash)

        agent.consume(gated.product, now=now)
        invocation = agent.invoke_skill(
            skill_dispatch["grant_request"]["skill_name"],
            arguments=arguments,
        )
        if not isinstance(invocation, SkillInvocation):  # pragma: no cover
            raise RuntimeError(f"skill dispatch returned {invocation!r}")
        detection = dict(invocation.output)
        _banner(
            narration,
            "STAGE 5 - AGENT: granted skill over governed context",
            {
                "agent": f"{definition.name}@{definition.artifact_version}",
                "archetypes": ", ".join(agent.identity.archetype_composition),
                "skill invoked": skill_dispatch["grant_request"][
                    "skill_name"
                ],
                "structured cycles found": detection["cycles_found"],
                "ring size": detection["cycle_length"],
                "ring members": detection["cycle_members"],
                "freshness "
                + f"({observation.observation_type})": str(retained),
            },
        )

        # --- Stage 6: REPLAY — record, serve, round-trip --------------------
        # `policy_bindings` is built here, from the pins the adopter reads off
        # `BootedFabric.pins`: D-06 keeps the SELECTION of which bindings are in
        # force in adopter hands, because dimension 2 assembled by a rule nobody
        # in the deployment wrote down is not an audit record.
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key="policy-bundle", version=policy_version),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=now,
            agent_conditioning=agent.perspective_conditioning(
                principal_id=perspective.principal_id, grant_set_hash=in_force
            ),
        )
        store = FileArtifactStore(root=root / "artifacts")
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store,
                artifact_class=governance.declaration["replay_record_class"],
            ),
        )
        _banner(
            narration,
            "STAGE 6 - REPLAY: the decision, recorded and served",
            {
                "replay record": served.replay_ref.content_address[:16]
                + "...",
                "dimensions": "fabric snapshot, policy bindings, model"
                " version, perspective, generation path",
                "skill-set in force": in_force[:16] + "...",
            },
        )

        print("")
        print("examples/08-e2e-demo: OK")

        if live:
            _live_narration(
                live_config=cast(
                    DeclaredArtifact, booted.artifacts["live-narration"]
                ).declaration,
                definition=definition,
                agent=agent,
                detection=detection,
                boundary=boundary,
            )

        return DemoResult(
            tenant_id=booted.tenant_id,
            artifacts=booted.artifacts,
            scenario=scenario,
            generated=generated,
            baseline_cycles=tuple(baseline),
            payment_rows=len(payment_rows),
            unattributed_rows=unattributed,
            envelopes_ingested=len(envelopes),
            resolved_seed_entities=resolved_seeds,
            product=gated.product,
            operators_invoked=execution.operators_invoked,
            detection=detection,
            agent=agent,
            definition=definition,
            definition_hash=definition_hash,
            granted_hash=granted,
            grant_set_hash=in_force,
            record=record,
            served=served,
            store=store,
            retained_freshness=retained,
            narration="\n".join(narration) + "\n",
            expected_narration=(ARTIFACTS / "expected_output.txt").read_text(
                encoding="utf-8"
            ),
        )
    finally:
        booted.handle.close()


def main(*, live: bool = False) -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-e2e-demo-") as scratch:
        run(root=Path(scratch), live=live)
    return 0


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
