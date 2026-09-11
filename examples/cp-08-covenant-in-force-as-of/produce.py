"""The spine: boot, acquire, govern. Three regions and nothing else.

There is no ``gate`` region, no ``record`` region and no ``serve`` region, and
no call to ``run_gates``, ``build_replay_record`` or ``serve`` — because the
door, both operators over L3, `Π`, the three L6 gates, the five-dimension
replay record, the query pins and the delivery are **one object the SDK owns**
(:func:`~ccf.products.resolver.build_governed_resolver`).

What is left here is this deployment's own seams: which config keys, which `Π`,
which `D_c`. Every argument below is a NAME or a callable, never a value.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import acquisition
import deployment
import projection

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
    """What one run produced, for a caller to inspect.

    The spine RETURNS its state rather than checking it, so assertions live
    where a test runner will actually run them.
    """

    tenant_id: str
    window: acquisition.FacilityWindow
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *, asked: ProductRequest, root: Path
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the question is not one this class answers — a bad question is a bad
    question rather than a broken deployment, and a verdict returned as a value
    cannot be swallowed by a bare ``except``.
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call derives, parses, registers and boots on the resulting pins.
    #    Connection values arrive HERE, from the caller — never from the config,
    #    which names the backend as a KIND only.
    booted = load_config_and_boot(
        HERE / "ccf_config.yaml",
        registry=registry,
        connection=deployment.connection(root=root),
    )
    # --8<-- [end:boot]

    # --8<-- [start:acquire]
    # 2. Both source legs at the bound governance resolved — `as_of` bounds the
    #    READ; `known_as_of` deliberately does not, because Π needs what the
    #    second clock excludes in order to say which axis excluded it. Then
    #    L1 -> L2. `booted.handle.worker` is the ONLY write handle to L3 in
    #    this process (single-writer, CLAUDE.md §10).
    #
    #    THE ORDER of those writes is a contract this deployment owns and
    #    asserts — see `deployment._edge`'s warning.
    window = deployment.acquire_for(booted, registry, asked)
    deployment.ingest(booted, window, at=asked.asked_at)
    # --8<-- [end:acquire]

    # --8<-- [start:govern]
    # 3. One object, owned by the SDK. Nothing below binds an operator, runs a
    #    gate, builds a record or serves a product.
    #
    # A NAMED function rather than a lambda, and the name is load-bearing: the
    # `D-IMPL-137` row-C predicate reads the tree for a `plan_factory` by name,
    # and a lambda is invisible to it.
    def plan_factory(
        *, required: tuple[str, ...], request: ProductRequest
    ) -> ProjectionPlan:
        return projection.CovenantInForceProjection(
            plan_id=scenario.plan_id,
            # The SDK's set, passed straight through. This deployment authors
            # no operator set, so there is nothing to diverge from.
            required=required,
            declared=projection.declaration(),
            # BOTH INSTANTS FROM THE EFFECTIVE REQUEST the SDK hands this
            # factory — after the class's relative defaults, policy bounds and
            # the backend capability have folded. Never the caller's raw
            # parameters, and never a value this spine resolved for itself.
            as_of=str(request.parameters[deployment.AS_OF]),
            known_as_of=str(request.parameters[deployment.KNOWN_AS_OF]),
        )

    def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
        return deployment.debt(view)

    scenario = deployment.CovenantScenario(
        window=window, asked=asked, booted_at=asked.asked_at
    )
    store = FileArtifactStore(root=root / "artifact-store")
    resolve = build_governed_resolver(
        fabric=booted,
        control_plane=registry,
        product_class_key=scenario.product_class_key,
        request_contract_key=scenario.request_contract_key,
        operator_parameter_keys=scenario.operator_parameter_keys,
        policy_bundle_key=scenario.policy_bundle_key,
        plan_factory=plan_factory,
        # An explicit scorer REPLACES the SDK's reference entirely. This
        # deployment measures its own `D_c` because the factor that moves is
        # whether the source carries an assertion time for each amendment,
        # which no reference scorer derives from a half-life table.
        debt_scorer=debt_scorer,
        capabilities=(deployment.traversal_capability(),),
        artifact_store=store,
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
        tenant_id=booted.tenant_id, window=window, product=outcome.product,
        record=record, served=outcome, store=store,
    )
