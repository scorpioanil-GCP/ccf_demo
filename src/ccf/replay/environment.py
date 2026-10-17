# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The supported replay environment — built from the record, not hand-assembled.

`D-IMPL-346`. SDK-defined mechanism (CLAUDE.md §11), and the thing six example
trees each wrote for themselves before it existed.

**The finding this closes, and it is the most-repeated one in the corpus.**
:class:`~ccf.replay.engine.ReplayEnvironment` is a Protocol of three methods,
and reconstructing a governed determination requires an implementation of it.
Nothing supplied one, so every tree that wanted to prove its own replay wrote
the same 40–95 lines:

``CP06C-F-01`` → ``CP13C-F-02`` → ``CP17-F-06`` → ``ATM-F-12`` → ``IBO-F-11``
→ ``UBO-F-12``

Six independent duplications of one shape is the
``docs/EXAMPLE-EVALUATION-CRITERIA.md`` §B.2 test — *"adopters would
predictably work around it, duplicate it, or get it wrong"* — being met rather
than approached. Every one of the six also reached the same private member to
bind operator parameters; that member is public as of this same decision.

**What this does NOT do, stated first.** It re-executes the recorded operator
path over the recorded snapshot and **re-derives nothing the record carries**.
The anchor instant, the debt in force, its evidence, the sources' refresh
recency and the obligation are copied off dimension 5 verbatim. Re-deriving any
of them would be a different decision wearing this one's identifier — the whole
point of replay is that the answer is reconstructed, not recomputed from a world
that has moved on.

**Nothing here is taken on trust, either.** Everything the environment returns
is checked by :func:`~ccf.replay.engine.replay`: a wrong plan fails the step
sequence, a wrong parameter set fails the parameter hash, a wrong envelope
fails the content address. This module makes the environment *easy to build
correctly*; the engine is still what makes it *true*.

**Its fabric is a READ-ONLY boot** (FW-2, whole-branch review I-1;
``D-IMPL-374``). Replay is read-only throughout, yet the reader that can answer
a classification read — every Policy-operator replay makes one — carries an
authority only ``ccf.boot.boot`` mints, and a writer boot takes the store's
cross-process writer lease. Beside a live serving writer on a persistent store
that boot is refused, so the replay road is
``load_config_and_boot(..., read_only=True)`` (or ``load_and_boot`` /
``ccf.boot.boot`` with the same keyword): the same governed reader, its views
stamped with the boot-minted authority, and no writer and no lease. A writer
boot still serves where no live writer holds the graph — a per-question
substrate reopened after its question closed it.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.deployment import build_operator_registry
from ccf.products.composite import ChildContractView
from ccf.products.composition import compose_expiry, compose_lineage
from ccf.products.contract import ContextProductContract, MaxTTL, ProductLineage
from ccf.products.provenance import EffectiveRequest
from ccf.products.resolver import (
    CompositePlanFactoryProtocol,
    build_governed_resolver,
)
from ccf.replay.record import CHILD_ADMITTED, ChildResolution, DecisionReplayRecord

if TYPE_CHECKING:
    from ccf.deployment import BootedFabric
    from ccf.products.product import OpenedProduct

__ccf_mode__ = "algorithmic"

__all__ = ["RecordedEnvironment", "RecordedEnvironmentUnbuildable"]


class RecordedEnvironmentUnbuildable(ValueError):
    """The record does not carry what rebuilding its environment requires.

    Raised rather than defaulted, because every value this environment needs is
    one the record either pinned or did not. Substituting a value resolved now
    would produce a reconstruction that ran against today's authority and said
    nothing about the decision — which is the failure replay exists to prevent.
    """


class RecordedEnvironment:
    """A :class:`~ccf.replay.engine.CompositeReplayEnvironment` built from one record.

    It answers both plan seams: :meth:`resolve_plan` for a decision that
    admitted no child, and :meth:`resolve_composite_plan` for one that did
    (`D-IMPL-389`, gap 3). A composite is rebuilt from its record and the
    children's contracts retained by content address; no producer is asked.

    **The supported way to replay from a process that did not answer the
    question** (`D-IMPL-378` R-A2 (a)). Opening a product boots nothing, so its
    Control Plane holds none of the declarations a record pins until a fabric is
    booted over it; a process that only opens the product and replays is refused
    at the first unresolvable pin
    (:class:`~ccf.replay.engine.ReplayUnresolvable`). Boot the recorded
    substrate through :func:`~ccf.deployment.load_config_and_boot` over the
    opened product's documents and Control Plane, then build this class; that
    registers what the documents declare, including the request contract, and
    asks nothing (``tests/replay/test_paved_replay_needs_its_environment.py``'s
    ``test_an_opened_product_replays_an_earlier_record_only_after_its_environment_is_built``).

    Args:
        record: The decision to reconstruct.
        opened: The product, opened against the deployment that produced it.
            Its :meth:`~ccf.products.product.OpenedProduct.build_arguments` is
            the documented escape hatch, and using it here is what keeps this
            class from becoming a second architecture: the resolver rebuilt
            below is the same one the serve path builds, from the same mapping.
        fabric: The booted fabric to read through. The caller opens this at the
            snapshot it wants; this class does not choose a substrate. Open it
            READ-ONLY — ``load_config_and_boot(..., read_only=True)`` — so the
            replay takes no writer lease and runs beside the live writer, in
            another process if need be; its reader stamps every view with the
            classification authority the boot mints from the pinned resolution
            spec, which is what lets a Policy operator re-execute (FW-2,
            whole-branch review I-1; ``D-IMPL-374``). A writer boot is
            accepted where no live writer holds the graph.

    Raises:
        RecordedEnvironmentUnbuildable: the record carries no request identity
            or no effective request, so Π cannot be rebuilt from it.
    """

    def __init__(
        self,
        *,
        record: DecisionReplayRecord,
        opened: OpenedProduct,
        fabric: BootedFabric,
    ) -> None:
        path = record.content_generation_path
        if path.request is None:
            raise RecordedEnvironmentUnbuildable(
                "the record carries no request identity, so there is nothing to"
                " rebuild the projection from (dimension 5 `request`)"
            )
        # Π is rebuilt from the EFFECTIVE request on dimension 2 — the class
        # defaults and policy bounds as they folded at decision time — never
        # from the caller's raw parameters and never from a value resolved now.
        resolution = record.policy_bindings.request_resolution
        effective = (
            EffectiveRequest.model_validate_json(resolution)
            if isinstance(resolution, str)
            else resolution
        )
        if not isinstance(effective, EffectiveRequest):
            raise RecordedEnvironmentUnbuildable(
                "dimension 2 carries no effective request, so the request this"
                f" decision actually ran under is unrecoverable: {resolution!r}"
            )

        arguments = opened.build_arguments(fabric)
        resolver = build_governed_resolver(**arguments)
        declaration = fabric.artifacts.get(resolver.product_class_key)
        if not isinstance(declaration, ProductClassDeclaration):
            raise RecordedEnvironmentUnbuildable(
                f"manifest key {resolver.product_class_key!r} resolves to no"
                " product-class declaration on this fabric"
            )

        self._record = record
        self._declaration = declaration
        self._plan_factory = resolver.plan_factory
        self._policy_key = resolver.policy_bundle_key
        # The class window, kept as the integer the serve passed to
        # `MaxTTL` (`compose_children`'s `max_ttl`), so a composite's floor is
        # recomputed against the same ceiling rather than a converted one.
        self._product_ttl_seconds = int(resolver.product_ttl_seconds)
        self._window = timedelta(seconds=self._product_ttl_seconds)
        self._request = path.request.model_copy(
            update={"parameters": dict(effective.values())}
        )
        self._required = tuple(path.operator_plan)
        self._operators = build_operator_registry(
            parameters=resolver.operator_parameters(self._request),
            view=fabric.handle.reader.as_of(
                tenant_id=record.tenant_id,
                at=record.context_fabric_snapshot.temporal_boundary,
            ),
            pins=fabric.pins,
            policy_bundle_key=self._policy_key,
        )

    @property
    def request(self) -> Any:
        """The effective request Π is rebuilt from, for a caller that needs it."""
        return self._request

    def resolve_plan(self, *, plan_id: str) -> Any:
        """The deployment's own plan factory, over the recorded operator set."""
        # `D-IMPL-389` (c), Dave 2026-10-17 09:41 MST. The engine calls this for
        # every record that admitted no child. For a COMPOSITE whose
        # requirements were walked and none admitted (an optional child
        # honestly absent), the serve still handed a child-aware factory an
        # EMPTY view (`src/ccf/products/resolver.py::GovernedResolver.__call__`),
        # so the same call is made here. A record with no child row, or a
        # factory without the capability, gets the plain call it always got.
        # The docstring above stays one line:
        # `tests/replay/test_step6_recorded_time.py` anchors a severing on it.
        if self._record.content_generation_path.child_resolutions and isinstance(
            self._plan_factory, CompositePlanFactoryProtocol
        ):
            return self._plan_factory.build_with_children(
                required=self._required,
                request=self._request,
                children=ChildContractView({}),
            )
        return self._plan_factory(required=self._required, request=self._request)

    def resolve_composite_plan(
        self, *, plan_id: str, children: ChildContractView
    ) -> Any:
        """The deployment's own plan factory over the RETAINED children, called as the serve called it.

        `D-IMPL-389` (gap 3; Dave, 2026-10-17 01:46 MST), on `D-IMPL-339`'s
        two-seams precedent. :func:`~ccf.replay.engine.replay` and the
        post-projection half of :func:`~ccf.replay.engine.replay_refusal`
        call this INSTEAD OF :meth:`resolve_plan` for a record that admitted
        at least one child; an environment without it is refused by name
        (``src/ccf/replay/engine.py::CompositeReplayEnvironment``), which is
        what made every composite decision unreplayable through
        :meth:`~ccf.products.product.OpenedProduct.replay_decision`.

        ``children`` is the view the engine rebuilt from the contracts the
        deciding fabric RETAINED by content address, each re-hashed against
        its row. Nothing here asks a producer, reads a provider or resolves
        a latest version.

        The factory is called exactly as
        ``src/ccf/products/resolver.py::GovernedResolver.__call__`` called it
        at decision time: ``build_with_children`` when it implements
        :class:`~ccf.products.resolver.CompositePlanFactoryProtocol`, decided
        structurally and never by probing a signature; the plain call
        otherwise. A factory without the capability is NOT refused: its
        serve built the plan without the children, which contributed
        governance only, so the plain call is the faithful one.

        As in :meth:`resolve_plan`, ``required`` is the recorded operator plan
        and ``plan_id`` is not consulted. Nothing is taken on trust: the
        engine holds the rebuilt plan to the recorded step sequence, query
        pins and content address, so a wrong plan diverges rather than passes.
        """
        if isinstance(self._plan_factory, CompositePlanFactoryProtocol):
            return self._plan_factory.build_with_children(
                required=self._required, request=self._request, children=children
            )
        return self._plan_factory(required=self._required, request=self._request)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        """The registry built at the recorded temporal boundary."""
        return self._operators

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: Any
    ) -> ContextProductContract:
        """The served contract, rebuilt with every recorded member copied verbatim.

        The payload and the plan id come from the re-executed projection; the
        anchor instant, the debt and its evidence, the refresh recency, the
        obligation and the empty finding come off dimension 5 unchanged. That
        split is the contract this method keeps: what the operators produced is
        reproduced, and what the fabric decided is retained.

        **A composite's lineage and expiry are rebuilt the way the serve built
        them** (`D-IMPL-336` F14), from members the record already carries on
        each ADMITTED child row (`R5`: ``child_operators_invoked``,
        ``child_policy_bundle_versions``, ``child_graph_snapshot_at`` and
        ``child_expires_at``): the lineage is the N-way union over the
        composite's own and every admitted child's
        (:func:`~ccf.products.composition.compose_lineage`), and the expiry is
        floored by the stalest admitted child
        (:func:`~ccf.products.composition.compose_expiry`), exactly as
        ``src/ccf/products/composite.py::compose_children`` composed them. A
        decision that admitted no child keeps its own lineage and window, as
        the serve did. An admitted row missing any of the four is refused
        (:class:`RecordedEnvironmentUnbuildable`), never defaulted.
        """
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        policy_versions = frozenset(
            binding.version
            for binding in record.policy_bindings.bindings
            if binding.key == self._policy_key
        )
        anchor = path.ttl_anchor_at or snapshot.temporal_boundary
        lineage = ProductLineage(
            operators_invoked=frozenset(path.operator_plan),
            policy_bundle_versions=policy_versions,
            graph_snapshot_at=snapshot.temporal_boundary,
        )
        expires_at = anchor + self._window
        admitted = tuple(
            row for row in path.child_resolutions if row.outcome_status == CHILD_ADMITTED
        )
        if admitted:
            lineage = compose_lineage([lineage, *(_child_lineage(row) for row in admitted)])
            expires_at = compose_expiry(
                constituent_validities=[_child_expiry(row) for row in admitted],
                max_ttl=MaxTTL(seconds=self._product_ttl_seconds),
                ttl_anchor_at=anchor,
            )
        return ContextProductContract(
            schema_name=self._declaration.schema_name,
            schema_version=self._declaration.schema_version,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=snapshot.temporal_boundary,
            expires_at=expires_at,
            ttl_anchor=self._declaration.ttl_anchor,
            ttl_anchor_at=path.ttl_anchor_at,
            lineage=lineage,
            payload=projection.payload,
            debt=path.debt,
            debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
            # SEC-020: the served product's empty finding, recorded on
            # dimension 5 and copied — never re-derived from the re-execution,
            # which for a withheld subject is the real read, not the masked one.
            computed_empty=path.computed_empty,
        )


def _unrecorded(row: ChildResolution, member: str) -> RecordedEnvironmentUnbuildable:
    """The refusal for an admitted row that does not carry what `R5` added."""
    return RecordedEnvironmentUnbuildable(
        f"the admitted child row for {row.required_product_class!r} carries no"
        f" `{member}`, so this composite's lineage and expiry cannot be rebuilt"
        " from its record (`D-IMPL-336` R5)"
    )


def _child_lineage(row: ChildResolution) -> ProductLineage:
    """One admitted child's lineage, as its row recorded it (`R5`)."""
    if row.child_operators_invoked is None:
        raise _unrecorded(row, "child_operators_invoked")
    if row.child_policy_bundle_versions is None:
        raise _unrecorded(row, "child_policy_bundle_versions")
    if row.child_graph_snapshot_at is None:
        raise _unrecorded(row, "child_graph_snapshot_at")
    return ProductLineage(
        operators_invoked=row.child_operators_invoked,
        policy_bundle_versions=row.child_policy_bundle_versions,
        graph_snapshot_at=row.child_graph_snapshot_at,
    )


def _child_expiry(row: ChildResolution) -> datetime:
    """One admitted child's own expiry, as its row recorded it (`R5`)."""
    if row.child_expires_at is None:
        raise _unrecorded(row, "child_expires_at")
    return row.child_expires_at
