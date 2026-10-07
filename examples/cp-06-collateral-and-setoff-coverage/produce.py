"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line is a CCF call an
adopter must make. There is **no domain vocabulary in it at all** — no
predicate, no table, no column, no asset class, no haircut, no number.
Everything specific to this deployment lives in ``deployment.py``,
``acquisition.py`` and ``projection.py`` beside it, and in the YAML beside
those.

[ADAPT] nothing.

**Three regions and no others** (`D-IMPL-314`): ``boot``, ``acquire``,
``govern``. There is no ``gate`` region, no ``record`` region and no ``serve``
region, and no call to ``run_gates``, ``build_replay_record`` or ``serve``
anywhere in this tree — the door, the graph view, both operators, Π, the three
L6 gates, the five-dimension replay record, the query pins and the delivery are
ONE object the SDK owns.

**The fourth validation gate is this product's own.** §D names an
over-allocation guard beyond the SDK's three: the sum of allocations against any
single asset must not exceed its haircut value. It is supplied as a
``product_gate`` — the SDK executes it at the ruled point and a breach becomes a
governed refusal, rather than this file checking a payload it has just built.

This file asserts nothing about the domain and prints nothing. What a run prints
is ``run.py``, which carries no marker region.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import acquisition
import deployment
import projection
from ccf.erasure import erasure_index_at
from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

HERE = Path(__file__).parent


@dataclass(frozen=True)
class Assembled:
    """What one run produced, for a caller to inspect."""

    tenant_id: str
    coverage: acquisition.Coverage
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(*, asked: ProductRequest,
                       root: Path) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the question is not one this class answers. A refusal is not an exception:
    a bad question is a bad question rather than a broken deployment, and a
    verdict returned as a value cannot be swallowed by a bare ``except``.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the single
    #    `ccf_config.yaml` names every section in force, and
    #    `load_config_and_boot` derives, parses, registers and boots on the
    #    resulting pins. Connection values arrive HERE, from the caller — never
    #    from the config, which names the backend as a KIND only.
    booted = load_config_and_boot(
        HERE / "ccf_config.yaml", registry=registry,
        connection=deployment.connection(root=root))
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # 2. The deployment reads its own two source stores at the scope
        #    governance allows, and hands back what it found; then L1 -> L2.
        #    `booted.handle.worker` is the ONLY write handle to L3 anywhere in
        #    this process (single-writer, CLAUDE.md §10).
        #
        #    The ORDER of those writes is a contract this deployment owns and
        #    asserts — thin edges first, attributed nodes last. See
        #    `deployment._edge`'s warning.
        coverage = deployment.acquire_for(booted, registry, asked)
        deployment.ingest(booted, coverage, at=asked.asked_at)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. The door, the graph view, both operators, Π, the three L6 gates,
        #    this product's own fourth gate, the five-dimension record, the
        #    query pins and the delivery are ONE object the SDK owns. What is
        #    left here is this deployment's seams: which config keys, which Π,
        #    which D_c, which invariant.
        #
        # A NAMED function rather than a lambda, and the name is load-bearing:
        # `D-IMPL-137`'s demand — that the Control Plane can see no second
        # operator set was authored — is a property something has to be able to
        # READ off this tree, and a lambda is unreadable to a static check.
        # This factory's ONLY operator source is the `required` tuple the SDK
        # hands it.
        def plan_factory(*, required: tuple[str, ...],
                         request: ProductRequest) -> ProjectionPlan:
            values = request.parameters
            return projection.CollateralCoverageProjection(
                plan_id=scenario.plan_id,
                required=required,
                declared=projection.declaration(),
                anchor=coverage.facility_id,
                commitment=Decimal(str(coverage.commitment or 0)),
                # Every one from the EFFECTIVE request the SDK hands this
                # factory, never from the caller's raw parameters.
                apply_haircuts=bool(values[deployment.APPLY_HAIRCUTS]),
                shared_collateral=str(values[deployment.SHARED_COLLATERAL]),
                jurisdiction_basis=str(values[deployment.JURISDICTION_BASIS]),
                enforceable_jurisdictions=coverage.enforceable_jurisdictions,
            )

        def debt_scorer(*, view: GraphView,
                        evidence: object = None) -> DebtAssessment:
            return deployment.debt(view)

        def product_gate(*, candidate: Any, evidence: object = None) -> str | None:
            """§D's fourth validation gate — the over-allocation guard.

            The SDK runs this at the ruled point and turns a returned reason
            into a governed refusal. Π computes the breach; the gate decides
            what it means, which is why the finding is data and this is a
            verdict.
            """
            over = candidate.payload["findings"]["over_allocated_assets"]
            if over:
                return (
                    f"over-allocation: {len(over)} asset(s) allocated beyond their"
                    f" haircut value, first {over[0]['uri']!r}"
                    f" ({over[0]['allocated']} > {over[0]['haircut_value']})"
                )
            return None

        scenario = deployment.CoverageScenario(coverage=coverage, asked=asked)
        store = FileArtifactStore(root=root / "artifact-store")
        resolve = build_governed_resolver(
            fabric=booted,
            control_plane=registry,
            product_class_key=scenario.product_class_key,
            request_contract_key=scenario.request_contract_key,
            operator_parameter_keys=scenario.operator_parameter_keys,
            policy_bundle_key=scenario.policy_bundle_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            product_gate=product_gate,
            artifact_store=store,
            # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
            erasure_index=erasure_index_at(store.root),
            replay_record_class="ccf.replay-record",
            query_pin_class="ccf.graph-query",
            max_ttl_seconds=scenario.max_ttl_seconds,
            product_ttl_seconds=scenario.product_ttl_seconds,
        )
        outcome = resolve(
            tenant=booted.tenant_id,
            product_class=asked.schema_name,
            version=asked.schema_version,
            perspective=deployment.perspective(),
            request=asked,
        )
        # --8<-- [end:govern]

        if not isinstance(outcome, ServedProduct):
            return outcome

        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=outcome.replay_ref.content_address))
        return Assembled(
            tenant_id=booted.tenant_id, coverage=coverage, product=outcome.product,
            record=record, served=outcome, store=store)
    finally:
        booted.handle.close()
