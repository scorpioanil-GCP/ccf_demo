"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
predicate, no table, no column, no entity class, no LEI and no number.
Everything specific to this deployment lives in ``deployment.py`` and
``acquisition.py`` beside it, and in the YAML beside those.

[ADAPT] nothing.

**Three regions, and no others** (`D-IMPL-314`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    load the one config, register what it puts in force, boot L2/L3
acquire read the two source stores and hand L1 envelopes to the one writer
govern  hand the whole governed seam to `GovernedResolver` in ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** No ``gate`` region, no
``record`` region, no ``serve`` region — no call to ``run_gates``,
``build_replay_record`` or ``serve`` anywhere in this tree. The door, the graph
view, the two operators, Π, the three L6 gates, the five-dimension replay
record, the query pins and the delivery are ONE object the SDK owns. cp-04, the
frozen specimen this succeeds, hand-composed all of them; the difference
between the two trees is the clearest statement of what the canonical path now
carries.

**The two depths are two authorities and never one number.** The caller's
``max_depth`` is request state: it folds through the class default, the
declared domain and the graph leg's technical capability, and the EFFECTIVE
value that survives is what acquisition walks at — recorded in replay dimension
2 as the request-contract binding (`D-IMPL-310`). The traversal operator's
``depth_limit`` is the BACKEND's ceiling, declared in ``ccf_config.yaml``. One
number serving as both would make a product decision look like a capability
limit.

This file asserts nothing about the domain and prints nothing. What a run
prints is ``run.py``, which carries no marker region, so no printed line is
published-snippet surface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
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
    family: acquisition.Family
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *, asked: ProductRequest, root: Path
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the question is not one this class answers. A refusal is not an exception:
    a bad question is a bad question rather than a broken deployment, and a
    verdict returned as a value cannot be swallowed by a bare ``except``.
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
        # 2. The deployment reads its own two source stores at the EFFECTIVE
        #    depth and hands back what it found; then L1 -> L2.
        #    `booted.handle.worker` is the ONLY write handle to L3 anywhere in
        #    this process (single-writer, CLAUDE.md §10), and ingestion happens
        #    here rather than inside the resolver because `GovernedResolver` is
        #    handed a fabric already populated.
        #
        #    The ORDER of those writes is a contract this deployment owns and
        #    asserts — see `deployment._edge_envelope`'s warning.
        family = deployment.acquire_for(booted, registry, asked)
        deployment.ingest(booted, family, at=asked.asked_at)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. The door, the graph view, both operators, Π, the three L6 gates,
        #    the five-dimension record, the query pins, the persisted append
        #    and the delivery are ONE object the SDK owns. What is left here is
        #    this deployment's own seams: which config keys, which Π, which D_c.
        #
        #    Every argument is a NAME or a callable, never a value: the six
        #    predicates, the backend depth ceiling, the family axis and the TTL
        #    figures all live in `ccf_config.yaml` and none is restated here.
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
            return projection.CorporateFamilyProjection(
                plan_id=scenario.plan_id,
                # The SDK's set, passed straight through. This deployment
                # authors no operator set at all, so there is nothing to
                # diverge from and no divergence guard to call.
                required=required,
                declared=projection.declaration(),
                # From the EFFECTIVE request the SDK hands this factory, never
                # from the caller's raw parameters and never from a value this
                # spine resolved for itself.
                max_depth=int(request.parameters[deployment.MAX_DEPTH]),
            )

        def debt_scorer(
            *, view: GraphView, evidence: object = None
        ) -> DebtAssessment:
            return deployment.debt(view)

        scenario = deployment.FamilyScenario(
            family=family, asked=asked, booted_at=asked.asked_at
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
            # AN EXPLICIT SCORER REPLACES THE SDK's REFERENCE ENTIRELY — the
            # two are alternatives rather than layers, and the SDK refuses a
            # call that supplies both. This deployment measures its own D_c
            # because the factor that moves is whether the ATTRIBUTE leg
            # resolved each served node, which no reference scorer can derive
            # from a half-life table. The SDK still places the assessment on
            # the product and routes on the declared bands.
            debt_scorer=debt_scorer,
            # The backend's own limit, so `max_depth` above it is refused with
            # authority `technical` and the bound that refused it.
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
            tenant_id=booted.tenant_id,
            family=family,
            product=outcome.product,
            record=record,
            served=outcome,
            store=store,
        )
    finally:
        booted.handle.close()
