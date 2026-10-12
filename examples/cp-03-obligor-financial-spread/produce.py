# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The spine — one question, end to end, for `credit-risk.spread`.

[MECHANISM] everything below the deployment seam. [ADAPT] nothing here: this
module names no obligor, no tag, no table, no ratio and no threshold. Every
value it works with arrives from `deployment.py`, which interprets the
documents beside it.

**The nine numbered steps are the specification's §D.2 read as code**, and the
ordering is not a convenience. `Policy` runs before anything reads graph state
(§D.3 step 2, composition invariant 1), the replay record is written before the
product is delivered (INV-CH7-79), and `ServableProduct` is not constructible
outside `run_gates` — so holding one IS the evidence the gates ran, rather than
a claim that they did.

**WHAT THIS RUNG ADDS TO THE SHAPE RUNGS 01 AND 02 ESTABLISHED.** One thing,
and it is visible in a signature rather than in a comment: :meth:`Scenario.debt`
takes **no view**. At rungs 01 and 02 the debt reading was measured over the
composed graph view, because those products carry one entity whose freshness is
one date. This product's freshness is not one date. The graph entity carries
*counts* — how many periods, how many peers — while every period keeps its own
`filed_date`, and §E.1's two decay rates are computed from those. So the
measurement's subject is the scenario, and the argument that would have pointed
at the view is absent because there is nothing in the view to measure. **§A's
claim that temporal validity is an ATTRIBUTE-level property is the reason this
method has a different arity from its neighbors'.**

**TWO REFUSALS ARE RETURNED AS DATA rather than raised.** A question this class
does not answer is a `ProductRequestViolation`; an anchor that resolves to no
obligor — or to an obligor with no facts — is an :class:`AnchorUnresolvable`.
Neither is an exception, because a bad question and a missing obligor are not
broken deployments, and a verdict returned as a value cannot be swallowed by a
bare `except`. §D.2 step 1 makes the unresolvable anchor a `404` and step 3
makes *"the obligor has no facts"* the same `404`: an empty spread is not a
spread of nothing, it is the absence of an answer, and serving `{}` would tell
the caller this company filed no financials.

**THE SEVEN CANONICAL REGIONS ARE THE PUBLISHED SNIPPET SURFACE.** They are
what the documentation page's ``--8<--`` includes address, and they are opened
in the order the fabric is called in — `boot`, `ingest`, `operators`, `project`,
`gate`, `record`, `serve`. Step 3 fills the stub's regions; it does not
renumber them.

AMENDED 2026-10-11 — compatibility repair (Dave, ruling 3 of 2026-10-11 16:23
MST; ``examples/AMENDMENTS-2026-10-11.md``). Everything above describes the
spine as it was frozen and is kept as that record. Its hand-composed half —
registering the MaxTTL and request contract, running the gates, building the
record, constructing the replay and query-pin writers, and overwriting the
policy operator's resolved parameters per principal — no longer exists on the
SDK's surface (``D-IMPL-353``/``D-IMPL-354``; ``D-IMPL-295``). Steps 3–9 now
run inside :func:`~ccf.products.resolver.build_governed_resolver`, over the
same declared operator, the same Π and the same D_c; the per-principal grant
reaches the operator as a governed request binding. The regions follow the
SDK's canonical shape (``D-IMPL-306``): ``boot``, ``acquire`` (the read, the
request check and the ingest), ``govern``. Both refusals-as-data above are
unchanged. The original text of this file is in git at the branch point.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.erasure import ErasureTrust, erasure_index_at
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtAssessment
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.contract import ContextProductContract
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
)
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope

class Scenario(Protocol):
    """What this spine asks a deployment to supply.

    Structural, never inherited: `deployment.py` satisfies this by having the
    members, not by importing anything from here. That is what keeps the
    dependency pointing one way — the spine knows the SHAPE of a deployment's
    answers and nothing about this particular product.
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]: ...

    @property
    def request(self) -> ProductRequest: ...

    @property
    def request_contract(self) -> ProductRequestContract: ...

    @property
    def request_contract_key(self) -> str: ...

    @property
    def product_class(self) -> ProductClassDeclaration: ...

    @property
    def perspective(self) -> Any: ...

    @property
    def operator_parameters(self) -> Mapping[str, Any]: ...

    @property
    def policy_bundle_key(self) -> str: ...

    # AMENDED 2026-10-11: what the governed resolver is wired with.
    @property
    def product_class_key(self) -> str: ...

    @property
    def half_life_key(self) -> str: ...

    @property
    def ttl_seconds(self) -> int: ...

    @property
    def effective_request(self) -> ProductRequest: ...

    @property
    def plan_id(self) -> str: ...

    @property
    def temporal_boundary(self) -> datetime: ...

    @property
    def now(self) -> datetime: ...

    @property
    def expires_at(self) -> datetime: ...

    @property
    def max_ttl_seconds(self) -> int: ...

    @property
    def replay_record_class(self) -> str: ...

    @property
    def query_pin_class(self) -> str: ...

    @property
    def artifact_store_dirname(self) -> str: ...

    def debt(self) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        **A method taking NOTHING, where rungs 01 and 02 took the view.** Debt
        is still MEASURED rather than declared — but what it is measured over
        is this product's per-period filing dates, and those are not in the
        graph. The entity L2 admitted carries `spread_periods` and
        `peer_comparison` as COUNTS; the dates each column decays from live on
        the scenario's periods. Handing this method a view would offer it
        something it must not read, and a measurement that reads the wrong
        subject is §E.1's finding rather than its demonstration.
        """


@dataclass(frozen=True)
class AnchorUnresolvable:
    """§D.2 steps 1 and 3's fail-closed refusal — `404`, never an empty payload.

    Returned as DATA, so a caller renders it rather than catching it.

    **Two conditions, one refusal, and collapsing them is deliberate.** The
    anchor may name no obligor at all, or it may name one this estate holds no
    facts for. §D.2 makes both a `404` because the distinction the caller could
    draw from separate answers is not one this product is willing to disclose:
    an LEI probe that could tell *no such obligor* from *an obligor with
    nothing filed* is an enumeration surface over the estate's coverage.

    **And an empty payload would be a false statement rather than a thin one.**
    A spread with no lines reads as *this company reported no financials*,
    which is a claim about the world. The absence of an answer is not an answer
    of zero — the same distinction §C.4 trap 5 draws inside the payload, drawn
    here at the payload's edge.
    """

    anchor: str
    status: int = 404
    reason: str = "anchor-unresolvable"


@dataclass(frozen=True)
class Assembled:
    """What one run produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so the assertions
    can live where a test runner will actually run them.

    :attr:`view` is the composed graph state Π ran over — the last readable
    evidence that the write path executed at all, and an empty one is what a
    mis-set boundary produces. :attr:`gated` is the
    :class:`~ccf.products.gates.ServableProduct` itself rather than only the
    contract inside it: the type is not constructible outside
    :func:`~ccf.products.gates.run_gates`, so holding one is direct evidence
    the gates ran.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    #: AMENDED 2026-10-11: the resolver's delivery — a ``ServedProduct``,
    #: produced only by ``DeliveryCapability.deliver`` over a
    #: ``ServableProduct`` after the record is appended. Holding it, with its
    #: record readable from the store, is the evidence the gates ran.
    gated: ServedProduct
    operators_invoked: frozenset[str]
    view: GraphView
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


class GovernedRefusal(RuntimeError):
    """The governed resolver refused a question this class otherwise answers.

    AMENDED 2026-10-11. Before the repair a gate refusal raised a bare
    ``RuntimeError`` naming the refusal; the resolver now returns it as a
    :class:`~ccf.products.refusal.RefusalEnvelope`, carried here so a caller
    can read its reason and replay reference.
    """

    def __init__(self, envelope: RefusalEnvelope) -> None:
        super().__init__(f"the governed resolver refused this question: {envelope!r}")
        self.envelope = envelope


def assemble_and_serve(
    *,
    config: Path,
    connection: Mapping[str, object],
    read: Callable[[BootedFabric, ProductRequest], Scenario | None],
    plan_class: Callable[..., ProjectionPlan],
    request: ProductRequest,
    root: Path,
    unsupported: Mapping[str, str] | None = None,
) -> Assembled | ProductRequestViolation | AnchorUnresolvable:
    """Answer one question, end to end, against ``root`` as scratch space.

    Raises:
        GovernedRefusal: the governed resolver refused a question that conforms
            to the request contract (AMENDED 2026-10-11).
    """
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot. The single
    #    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    #    derives and parses all of them, registers the `role: register` ones,
    #    and boots on the resulting pins. Connection values arrive HERE, from
    #    the caller — never from the config, which declares the backend as a
    #    KIND only. A DSN inside a content-hashed artifact is a DSN persisted
    #    into the audit plane forever.
    booted = load_config_and_boot(config, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # The one line that crosses the deployment seam: the deployment names
        # its own artifact keys, reads its own store, and hands back this
        # question's values.
        #
        # `None` means the anchor resolved to nothing, or to an obligor this
        # estate holds no facts for. §D.2 makes both a 404 BEFORE the graph is
        # touched — there is no ingest, no view and no projection for a spread
        # that does not exist, and inventing an empty one to keep a happy path
        # alive is the defect this branch prevents.
        scenario = read(booted, request)
        if scenario is None:
            return AnchorUnresolvable(anchor=request.subject)

        # THE DOOR's first check, kept here so a question this class does not
        # answer is still returned as a `ProductRequestViolation` before the
        # graph is touched. `debt_tolerance` is REQUIRED with no default (§B.4).
        # The resolver repeats the check over the effective request.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3
        #    anywhere in this process (single-writer, CLAUDE.md §10,
        #    INV-CH7-10). The Postgres estate this deployment READ from is not
        #    reachable from here at all.
        #
        #    ONE ENVELOPE, and `deployment.source_read` says why at length: every
        #    signal class shares this product's single `match_key`, so the
        #    idempotent upsert would merge them into one entity anyway.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. Π at L5, constructed by the fabric from the `required` set the SDK
        #    hands it — the product class's own document — so there is no
        #    second authored operator set to diverge from. A NAMED function, so
        #    a static check can read that its only operator source is
        #    `required`. The D_c is this deployment's own, measured over the
        #    per-period filing dates (the view is kept only as the last
        #    readable evidence the write path executed).
        witnessed: dict[str, GraphView] = {}

        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return plan_class(
                plan_id=scenario.plan_id, required=required, scenario=scenario
            )

        def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
            witnessed["view"] = view
            return scenario.debt()

        # 4. The governed resolver. It registers this class's MaxTTL and
        #    request surface from the deployment's declarations, builds the ONE
        #    declared operator (`policy.principal-subgraph`, its admitted set
        #    bound to the effective request's `jurisdictions`), runs Π, holds
        #    the claimed lineage to what ran, runs the three L6 gates — the
        #    `ttl-bounds` refusal over the latest filing is gate 3's, as before
        #    — and appends the record BEFORE anything is delivered.
        store = FileArtifactStore(
            root=root / scenario.artifact_store_dirname,
            write_kinds=WriteKinds.declare(
                {
                    scenario.replay_record_class: (ReplayMint,),
                    scenario.query_pin_class: (ReplayMint,),
                    ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
                }
            ),
        )
        resolve = build_governed_resolver(
            fabric=booted,
            control_plane=registry,
            product_class_key=scenario.product_class_key,
            request_contract_key=scenario.request_contract_key,
            operator_parameter_keys=tuple(scenario.operator_parameters),
            policy_bundle_key=scenario.policy_bundle_key,
            plan_factory=plan_factory,
            debt_scorer=debt_scorer,
            # The λ_c table the `from_entity_freshness` expiry runs from.
            evidence_clock_key=scenario.half_life_key,
            artifact_store=store,
            # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
            erasure_trust=ErasureTrust(authorities={}),
            erasure_index=erasure_index_at(store.root),
            replay_record_class=scenario.replay_record_class,
            query_pin_class=scenario.query_pin_class,
            max_ttl_seconds=scenario.max_ttl_seconds,
            product_ttl_seconds=scenario.ttl_seconds,
        )

        # 5. Ask. A refusal is a value; this specimen promises a served answer,
        #    so a refusal is raised by name with its envelope.
        served = resolve(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=scenario.effective_request,
        )
        if not isinstance(served, ServedProduct):
            # §B.2: A SUPPRESSED OBLIGOR MUST READ EXACTLY LIKE AN ABSENT ONE.
            # Before the repair a principal granted nothing received a product
            # with no obligor in it, which the assembler then refused as the
            # §D.2 404. The resolver now anchors the expiry on the admitted
            # view, so the same principal's question is refused one step
            # earlier — no evidence instant in an empty view — with its record
            # written. The caller receives the 404 an absent obligor receives;
            # the audit plane keeps the account.
            admitted = witnessed.get("view")
            if served.reason == "ttl-anchor-unresolvable" and admitted is not None and not any(
                True for _ in admitted.entities
            ):
                return AnchorUnresolvable(anchor=request.subject)
            raise GovernedRefusal(served)
        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=served.replay_ref.content_address)
        )
        # --8<-- [end:govern]

        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=served.product,
            gated=served,
            # From the RECORD's own account of the plan.
            operators_invoked=frozenset(record.content_generation_path.operator_plan),
            view=witnessed["view"],
            record=record,
            served=served,
            store=store,
        )
    finally:
        booted.handle.close()
