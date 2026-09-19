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

from decimal import Decimal

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import acquisition
import deployment
import projection

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
    window: acquisition.FacilityWindow
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *, asked: ProductRequest, root: Path, at_transaction: str | None = None
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
    # `at_transaction` REPLAYS: the source read is bounded at a transaction
    # point a previous run recorded, so the same question against an advanced
    # ledger returns the same answer. `None` — the default — reads the head.
    window = deployment.acquire_for(booted, registry, asked,
                                    at_transaction=at_transaction)
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

    # THE DECLARED INVARIANT, implemented where only this deployment can know
    # it. The SDK ships the machinery and stamps the gate's governed identity
    # onto any refusal; what counts as coherent is this product's to say.
    def product_gate(*, candidate: Any, evidence: object = None) -> str | None:
        return deployment.temporal_coherence_violation(candidate)

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
        # NO `debt_scorer`, deliberately: the SDK's REFERENCE assessment
        # applies (`CP-SPEC-008` §E.2). This product had a scorer of its own —
        # placeable ÷ served on the assertion axis — and it was withdrawn with
        # the population claim it rested on: every facility amendment in this
        # estate carries a booking date, so the ratio was 1 and `D_c` 0 on
        # every answer. See `spec/MEASUREMENT-NOTE.md` §2.
        #
        # The reference path is DEFAULTLESS by design — omitting all four of
        # these is refused rather than silently scored — so the deployment
        # names its two Control Plane tables and DECLARES the two factors the
        # SDK cannot measure.
        #
        # MEASURED TWICE, AND SAID PLAINLY. Until `D-IMPL-341` `D_c` read 0 on
        # every answer this product could serve: freshness was the term that
        # would move, but every observation was dated by the run that ingested
        # it, so it was 1 by construction. Since 341 (validation pass
        # 2026-09-18) each amendment claim carries its BOOKING date as its own
        # instant and the `amendment` row decays on it, so freshness ages from
        # the ledger's clock — 0.94 on the demonstration facility's booking day,
        # 0.83 at the end of its 180-day window — and `D_c` moves with it. The
        # other two factors are declared 1 against a measured estate. §E.2 is
        # the claim this implements: the platform's assessment applies. What
        # was removed before was not a working signal but a per-run ratio
        # DRESSED as one; what moves now is the reference curve on real dates.
        half_life_key="half_life",
        debt_profile_key="debt_profile",
        declared_completeness=Decimal(deployment.declared_debt_factor("completeness")),
        declared_semantic_consistency=Decimal(
            deployment.declared_debt_factor("semantic_consistency")
        ),
        product_gate=product_gate,
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
