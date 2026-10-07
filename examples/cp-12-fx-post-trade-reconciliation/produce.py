"""The spine: CCF's calls, and none of this deployment's vocabulary.

[MECHANISM] everything here. [ADAPT] nothing.

Three regions — boot, acquire, govern. The door, the graph view, both
operators, Π, the universal gates, the declared product gate, the
five-dimension replay record, the query pins, the persisted append, the Context
Debt assessment and the delivery are ONE object the SDK owns.

**No local binder, no hand-rolled gate, no hand-rolled replay, no local serve,
no local debt scorer** (`D-IMPL-315`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import acquisition
import deployment
import projection
from ccf.erasure import erasure_index_at
from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot
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
    estate: acquisition.Estate
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore
    registry: ControlPlaneRegistry


def assemble_and_serve(
    *, asked: ProductRequest, root: Path,
    registry: ControlPlaneRegistry | None = None,
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the product refuses. A governed *no* is an answer, and a verdict returned
    as a value cannot be swallowed by a bare ``except``.
    """
    registry = registry if registry is not None else ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the whole registration prologue and the boot: the
    #    single `ccf_config.yaml` names every section in force, and
    #    `load_config_and_boot` derives, parses, registers and boots on the
    #    resulting pins. Connection values arrive HERE, from the caller.
    booted = load_config_and_boot(
        HERE / "ccf_config.yaml",
        registry=registry,
        connection=deployment.connection(root=root),
    )
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # 2. The deployment reads its own two source stores — PostgreSQL for
        #    the values, Fluree for the instants — and hands back what it
        #    found; then L1 -> L2. `booted.handle.worker` is the ONLY write
        #    handle to L3 anywhere in this process (single-writer, §10).
        #
        #    The ORDER of those writes is a contract this deployment owns and
        #    asserts — see `deployment._edge`'s warning.
        estate = deployment.acquire_for(asked)
        deployment.ingest(booted, estate, at=asked.asked_at)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. Everything governed is ONE object the SDK owns. What is left here
        #    is this deployment's own seams: which config keys, which Π, and
        #    the deployment half of the ONE gate its class declares.
        #
        # A NAMED function rather than a lambda, and the name is load-bearing:
        # `D-IMPL-137`'s demand — that the Control Plane can see no second
        # operator set was authored — has to be READABLE off this tree, and a
        # lambda is unreadable to a static check.
        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return projection.FXReconciliationProjection(
                plan_id=scenario.plan_id,
                # The SDK's set, passed straight through. This deployment
                # authors no operator set at all.
                required=required,
                declared=scenario.declared,
            )

        scenario = deployment.ReconciliationScenario(estate=estate, asked=asked)
        store = FileArtifactStore(root=root / "artifact-store")
        resolve = build_governed_resolver(
            fabric=booted,
            control_plane=registry,
            product_class_key=scenario.product_class_key,
            request_contract_key=scenario.request_contract_key,
            operator_parameter_keys=scenario.operator_parameter_keys,
            policy_bundle_key=scenario.policy_bundle_key,
            plan_factory=plan_factory,
            # NO `debt_scorer`. The SDK's reference assessment runs off the
            # registered λ_c table and the declared debt profile — and it ages
            # against the RECORDED instant, which is the whole of `FXR-G24`.
            half_life_key="half_life",
            debt_profile_key="debt_profile",
            # The two factors the SDK says it has no measurement for, measured
            # on the estate read and handed over. `F` is the SDK's.
            declared_completeness=deployment.measured_completeness(estate),
            declared_semantic_consistency=(
                deployment.measured_semantic_consistency(estate)
            ),
            # THE DEPLOYMENT HALF OF ONE DECLARED GATE. Identity is in
            # `ccf_config.yaml`; the resolver stamps it onto the refusal.
            product_gate=deployment.build_verdict_gate(asked=asked),
            artifact_store=store,
            # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
            hitl_policy_key="hitl_policy",
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
            store.get(content_address=outcome.replay_ref.content_address)
        )
        return Assembled(
            tenant_id=booted.tenant_id, estate=estate, product=outcome.product,
            record=record, served=outcome, store=store, registry=registry,
        )
    finally:
        booted.handle.close()
