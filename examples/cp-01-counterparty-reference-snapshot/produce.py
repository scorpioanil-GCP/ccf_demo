"""The spine — one question, end to end, for `reference.counterparty.v1`.

[MECHANISM] everything below the deployment seam. [ADAPT] nothing here: the
whole point of this module is that it names no counterparty, no jurisdiction,
no table and no threshold. Every value it works with arrives from
`deployment.py`, which in turn interprets the documents beside it.

**The nine numbered steps are the specification's §D.2 read as code**, and the
ordering is not a convenience. `Policy` runs before anything reads graph state
(Standard §10.3), the replay record is written before the product is delivered
(INV-CH7-79), and `ServableProduct` is not constructible outside `run_gates` —
so holding one IS the evidence the gates ran, rather than a claim that they did.

**TWO REFUSALS ARE RETURNED AS DATA rather than raised.** A question this class
does not answer is a `ProductRequestViolation`; an anchor that resolves to no
entity is an :class:`AnchorUnresolvable`. Neither is an exception, because a bad
question and a missing entity are not broken deployments — and a verdict
returned as a value cannot be swallowed by a bare ``except``. §D.2 step 1 is
explicit that an unresolvable anchor is a `404` and *"never an empty payload"*.

AMENDED 2026-10-11 — compatibility repair (Dave, ruling 3 of 2026-10-11 16:23
MST; ``examples/AMENDMENTS-2026-10-11.md``). Everything above describes the
spine as it was frozen, and is kept as that record. The hand-composed half of
it — registering the MaxTTL and the request contract, running the gates,
building the record, constructing the replay and query-pin writers — no longer
exists on the SDK's surface: since ``D-IMPL-353``/``D-IMPL-354`` a Control
Plane registration or a replay write needs a capability only an SDK
composition root can mint. So those steps now run inside the SDK's
:func:`~ccf.products.resolver.build_governed_resolver`, which registers the
class from this deployment's declarations, executes the same declared
operator, Π, the three L6 gates and the five-dimension record, and serves.
The marker regions follow the SDK's canonical shape (``D-IMPL-306``): ``boot``
is unchanged; ``acquire`` is the old ``ingest`` with the deployment's read and
the request check before it; ``govern`` hands the resolver the same Π and the
same D_c this deployment always computed, composes it, and asks it the
question. The calling principal's jurisdiction grant, which this spine used to
write over the resolved policy artifact at runtime (an ungoverned write the SDK
retired at ``D-IMPL-295``), is now STATED on the request as ``jurisdictions``
and reaches the policy operator through the declared request binding. The
question, the operator, the TTL, the debt arithmetic and the payload are the
deployment's, unchanged. The original text of this file is in git at the
specimen's branch point.
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
from ccf.halflife.debt import DebtAssessment
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

    # AMENDED 2026-10-11: the placed keys the governed resolver resolves by,
    # and the declared product lifetime it anchors the expiry with.
    @property
    def product_class_key(self) -> str: ...

    @property
    def half_life_key(self) -> str: ...

    @property
    def ttl_seconds(self) -> int: ...

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

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question actually assembled (whitepaper §7.7).

        A method, and it takes the view, because debt is MEASURED against the
        assembly rather than declared beside it.
        """


@dataclass(frozen=True)
class AnchorUnresolvable:
    """§D.2 step 1's fail-closed refusal — `404`, never an empty payload.

    Returned as DATA, so a caller renders it rather than catching it. The
    distinction the specification draws is worth keeping in the type system:
    *no such entity* and *an entity with nothing in it* are different answers,
    and a product that returns the second for the first has told the caller
    something false about the world.
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
    mis-set boundary produces. :attr:`gated` was the
    :class:`~ccf.products.gates.ServableProduct` itself (AMENDED 2026-10-11:
    now the resolver's ``ServedProduct``; see the field) rather than only the
    contract inside it: the type is not constructible outside
    :func:`~ccf.products.gates.run_gates`, so holding one is direct evidence the
    gates ran.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    #: AMENDED 2026-10-11: the resolver's delivery. The gates run inside the
    #: SDK's resolver, whose only path to a ``ServedProduct`` is
    #: ``DeliveryCapability.deliver`` over a ``ServableProduct`` after the
    #: record is appended — so holding this, with its record readable from the
    #: store, is the evidence the gates ran.
    gated: ServedProduct
    operators_invoked: frozenset[str]
    view: GraphView
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore


class GovernedRefusal(RuntimeError):
    """The governed resolver refused a question this class otherwise answers.

    AMENDED 2026-10-11. Before the repair a gate refusal raised a bare
    ``RuntimeError`` from this module; the resolver now returns it as a
    :class:`~ccf.products.refusal.RefusalEnvelope`, carried here so a caller
    can read its reason and replay reference rather than a message about them.
    """

    def __init__(
        self, envelope: RefusalEnvelope, *, view: GraphView | None = None
    ) -> None:
        super().__init__(f"the governed resolver refused this question: {envelope!r}")
        self.envelope = envelope
        #: The admitted view the deployment's D_c was scored over, when the
        #: resolver got that far — so a caller can tell an EMPTY admission from
        #: any other refusal without the refusal text saying which.
        self.view = view


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
    #    KIND only.
    booted = load_config_and_boot(config, registry=registry, connection=connection)
    # --8<-- [end:boot]
    try:
        # --8<-- [start:acquire]
        # The one line that crosses the deployment seam: the deployment names
        # its own artifact keys and hands back this question's values —
        # including the calling principal's grant, stated on the request.
        #
        # `None` means the anchor resolved to nothing. §D.2 step 1 makes that a
        # 404 BEFORE the graph is touched — there is no ingest, no view and no
        # projection for an entity that does not exist.
        scenario = read(booted, request)
        if scenario is None:
            return AnchorUnresolvable(anchor=request.subject)

        # THE DOOR's first check, kept here so a question this class does not
        # answer is still returned as a `ProductRequestViolation` before the
        # graph is touched. The resolver repeats it; the two read one contract.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        # 2. L1 → L2. `booted.handle.worker` is the ONLY write handle to L3
        #    anywhere in this process (single-writer, CLAUDE.md §10,
        #    INV-CH7-10). The source estate this deployment READ from is not
        #    reachable from here at all.
        for envelope in scenario.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:acquire]

        # --8<-- [start:govern]
        # 3. Π at L5, constructed by the fabric from the `required` set the SDK
        #    hands it — the product class's own document. A NAMED function, so
        #    a static check can read that its only operator source is
        #    `required`. The D_c scorer is this deployment's own, measured over
        #    the view the operator left standing; the view is kept for the
        #    caller as the last readable evidence the write path executed.
        witnessed: dict[str, GraphView] = {}

        def plan_factory(
            *, required: tuple[str, ...], request: ProductRequest
        ) -> ProjectionPlan:
            return plan_class(
                plan_id=scenario.plan_id, required=required, scenario=scenario
            )

        def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
            witnessed["view"] = view
            return scenario.debt(view)

        # 4. The governed resolver. It registers this class's MaxTTL and request
        #    surface from the deployment's declarations, builds the L4 registry
        #    from the declared parameter set (the policy operator's admitted
        #    set bound to the request's `jurisdictions`), runs Π, holds the
        #    claimed lineage to what ran, runs the three L6 gates — the TTL gate
        #    included, which is where this product's §F.4 finding surfaces — and
        #    builds the five-dimension record before anything is delivered. The
        #    store declares what the fabric's own writers file into it.
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

        # 5. Ask. The record is persisted BEFORE the product is delivered
        #    (INV-CH7-79). A refusal is a value; it is RAISED here by name, with
        #    its envelope, because the run producing it is the evidence the
        #    finding is taken back with.
        served = resolve(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=scenario.request,
        )
        if not isinstance(served, ServedProduct):
            raise GovernedRefusal(served, view=witnessed.get("view"))
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
