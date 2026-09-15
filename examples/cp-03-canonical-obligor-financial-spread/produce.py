"""Assemble one typed Context Product and serve it, end to end.

**This file is the fabric's half.** [MECHANISM] Every line here is a CCF call
an adopter must make. There is **no domain vocabulary in it at all** — no
table, no column, no tag, no ratio, no LEI and no number. Everything specific
to this deployment lives in ``deployment.py`` and ``acquisition.py`` beside it,
and in the YAML beside those.

[ADAPT] nothing.

**Three regions, and no others** (`D-IMPL-314`):

======  ====================================================================
marker  what the fabric does
======  ====================================================================
boot    load the one config, register what it puts in force, boot L2/L3
acquire read the source store and hand L1 envelopes to the one writer
govern  hand the whole governed seam to `GovernedResolver` in ONE call
======  ====================================================================

**What is NOT here, and their absence is the point.** No ``gate`` region, no
``record`` region, no ``serve`` region — no call to ``run_gates``,
``build_replay_record`` or ``serve`` anywhere in this tree. The door, the graph
view, the operator, Π, the three L6 gates, the product's own declared gate, the
five-dimension replay record, the query pins and the delivery are ONE object
the SDK owns. The frozen specimen this succeeds hand-composed all of them, and
its call to ``build_replay_record`` without a resolution binding is one of the
two defects that keep it from serving (`CP14-F-22`); the difference between the
two trees is the clearest statement of what the canonical path now carries.

This file asserts nothing about the domain and prints nothing. What a run
prints is ``run.py``, which carries no marker region, so no printed line is
published-snippet surface.
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
    read: acquisition.SpreadRead
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


def assemble_and_serve(
    *, asked: ProductRequest, root: Path, principal_id: str | None = None
) -> Assembled | RefusalEnvelope:
    """Answer one question, end to end, against ``root`` as scratch space.

    Returns a :class:`~ccf.products.refusal.RefusalEnvelope` **as data** when
    the question is not one this class answers, or when what it assembled is
    not servable: a wrong intent, an out-of-domain parameter, an obligor the
    principal may not see, a spread outside its declared window, a debt above
    the caller's tolerance. A refusal is not an exception: a bad question is a
    bad question rather than a broken deployment, and a verdict returned as a
    value cannot be swallowed by a bare ``except``.

    ``principal_id`` asks as somebody other than the declared default
    perspective; the request's ``jurisdictions`` must then state that
    principal's grant (``deployment.request`` does so).
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
        # 2. The deployment reads its source store at the EFFECTIVE parameters
        #    and hands back what it found; then L1 -> L2, one dated envelope per
        #    obligor, period, line and cohort statistic.
        #    `booted.handle.worker` is the ONLY write handle to L3 anywhere in
        #    this process (single-writer, CLAUDE.md §10), and ingestion happens
        #    here rather than inside the resolver because `GovernedResolver` is
        #    handed a fabric already populated.
        read = deployment.acquire_for(booted, registry, asked, principal_id=principal_id)
        deployment.ingest(booted, read, at=asked.asked_at)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. The door, the graph view, the operator, Π, the three L6 gates, the
        #    product's own declared gate, the five-dimension record, the query
        #    pins, the persisted append and the delivery are ONE object the SDK
        #    owns. What is left here is this deployment's own seams: which
        #    config keys, which Π, which D_c, which invariant.
        #
        #    Every argument is a NAME or a callable, never a value: the window,
        #    the λ_c table, the bands and the grant axis all live in the tree's
        #    documents and none is restated here.
        #
        # A NAMED function rather than a lambda, and the name is load-bearing.
        # `D-IMPL-137`'s demand — that the Control Plane can see no second
        # operator set was authored — is a property something has to be able to
        # READ off this tree. A named factory whose ONLY operator source is the
        # `required` tuple the SDK hands it makes that provable.
        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return projection.FinancialSpreadProjection(
                plan_id=scenario.plan_id,
                # The SDK's set, passed straight through. This deployment
                # authors no operator set at all.
                required=required,
                # From the EFFECTIVE request the SDK hands this factory, never
                # from a value this spine resolved for itself.
                subject=request.subject,
            )

        def debt_scorer(
            *, view: GraphView, evidence: object = None
        ) -> DebtAssessment:
            # The λ_c table and the D_c bands are the BOOTED artifacts — the
            # exact documents the pins record — never a second parse.
            return deployment.debt(
                view,
                now=asked.asked_at,
                half_life=booted.artifacts[scenario.half_life_key],
                profile=booted.artifacts[scenario.debt_profile_key],
            )

        scenario = deployment.SpreadScenario(read=read, asked=asked)
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
            # two are alternatives rather than layers. This deployment measures
            # its own D_c because the factors that move are per-column decay
            # under two signal classes and the evaluable fraction of declared
            # lines, which no reference scorer can derive from a table alone.
            # The bands the served product routes on are still the declared
            # profile's, named by key.
            debt_scorer=debt_scorer,
            debt_profile_key=scenario.debt_profile_key,
            # THE PRODUCT'S OWN INVARIANT, declared by identity in the config
            # and supplied as a predicate here (`D-IMPL-282` R-11). The
            # resolver stamps the declared gate id on any refusal it returns.
            product_gate=deployment.freshness_window_gate(
                ttl_seconds=scenario.product_ttl_seconds
            ),
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
            perspective=deployment.perspective(principal_id=principal_id),
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
            read=read,
            product=outcome.product,
            record=record,
            served=outcome,
            store=store,
        )
    finally:
        booted.handle.close()
