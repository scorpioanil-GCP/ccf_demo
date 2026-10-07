"""The spine: CCF's calls, and none of this deployment's vocabulary.

[MECHANISM] everything here. [ADAPT] nothing.

Three regions — boot, acquire, govern — and what is left between them is this
deployment's own seams: which config, which Π, which declared gate. The door,
the graph view, both operators, Π, the universal gates, the declared product
gate, the five-dimension replay record, the query pins, the persisted append,
the Context Debt assessment and the delivery are ONE object the SDK owns.

**No local binder, no hand-rolled gate, no hand-rolled replay, no local serve.**
`GovernedResolver` is handed the seam and performs all four (`D-IMPL-315`).
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
    """What one run produced, for a caller to inspect.

    The spine RETURNS its state rather than checking it, so assertions live
    where a test runner will actually run them.
    """

    tenant_id: str
    estate: acquisition.Estate
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *, asked: ProductRequest, root: Path
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the product refuses — a stale mandatory signal, a debt figure over the
    caller's tolerance, a TTL past its ceiling. A refusal is not an exception:
    a governed *no* is an answer, and a verdict returned as a value cannot be
    swallowed by a bare ``except``.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the whole registration prologue and the boot: the
    #    single `ccf_config.yaml` names every section in force, and
    #    `load_config_and_boot` derives, parses, registers and boots on the
    #    resulting pins. Connection values arrive HERE, from the caller — never
    #    from the config, which names the backend as a KIND only.
    booted = load_config_and_boot(
        HERE / "ccf_config.yaml",
        registry=registry,
        connection=deployment.connection(root=root),
    )
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # 2. The deployment reads its own two source stores at the decision
        #    instant and hands back what it found; then L1 -> L2.
        #    `booted.handle.worker` is the ONLY write handle to L3 anywhere in
        #    this process (single-writer, CLAUDE.md §10), and ingestion happens
        #    here because `GovernedResolver` is handed a fabric already
        #    populated.
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
        # A NAMED function rather than a lambda, and the name is load-bearing.
        # `D-IMPL-137`'s demand — that the Control Plane can see no second
        # operator set was authored — is a property something has to be able to
        # READ off this tree. A lambda is unreadable to a static check; a named
        # factory whose ONLY operator source is the `required` tuple the SDK
        # hands it makes that provable rather than merely true.
        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return projection.TreasuryLiquidityProjection(
                plan_id=scenario.plan_id,
                # The SDK's set, passed straight through. This deployment
                # authors no operator set at all, so there is nothing to
                # diverge from and no divergence guard to call.
                required=required,
                declared=scenario.declared,
            )

        scenario = deployment.TreasuryScenario(estate=estate, asked=asked)
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
            # registered half-life table and the declared debt profile, which
            # is the whole point of declaring per-class λ_c: a deployment that
            # scored its own D_c here would be answering the question the
            # Control Plane was configured to answer.
            half_life_key="half_life",
            debt_profile_key="debt_profile",
            # THE TWO FACTORS THE SDK HAS NO MEASUREMENT FOR, measured by the
            # deployment and handed over. `F` is the SDK's, from the registered
            # λ_c table over the observation ages; the fold and the band
            # routing are the SDK's too. Nothing in this example computes
            # `D_c`.
            declared_completeness=deployment.measured_completeness(estate),
            declared_semantic_consistency=(
                deployment.measured_semantic_consistency(estate)
            ),
            # THE DEPLOYMENT HALF OF ONE DECLARED GATE. Its identity is in
            # `ccf_config.yaml`; the resolver stamps `gate` and `gate_version`
            # onto the refusal, so this predicate cannot claim to be a gate its
            # class did not declare.
            product_gate=deployment.build_staleness_gate(asked=asked),
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
            tenant_id=booted.tenant_id,
            estate=estate,
            product=outcome.product,
            record=record,
            served=outcome,
            store=store,
        )
    finally:
        booted.handle.close()
