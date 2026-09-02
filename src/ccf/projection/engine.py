"""Two-stage execution: the operator plan, then Π (INV-CH7-42).

Whitepaper §7.4–§7.5; DESIGN.md §2B.1 (planner) and §2B.2 (two-stage
execution).

**Stage 1 — what is true.** The engine hands the plan's declared operator keys
to :func:`ccf.operators.planner.build_operator_plan`, which resolves them
against the registry and imposes the canonical dependency order — then splits
that sequence at its non-pushable boundaries
(:func:`ccf.projection.segmentation.segment_plan`) and issues **one
``reader.query()`` per pushable segment** (`GQ-14` at
docs/GRAPH_QUERY_SEMANTICS.md:289; the `D-IMPL-87` at docs/DECISIONS.md
resolution). Each pushed segment's operators are then **re-applied** over the
segment's answer through the per-execution
:class:`~ccf.operators.planner.IntermediateCache` — sound because the answer
is a fixed point of its own operators (`GQ-19` at
docs/GRAPH_QUERY_SEMANTICS.md:356), and required because every provenance
fact the engine records is execution-derived, never plan-side prediction.
In-process segments run over the current view exactly as before, and the
entity URIs they leave behind become the next pushed segment's
``allowed_entities`` under the uniform rule (`GQ-15` at
docs/GRAPH_QUERY_SEMANTICS.md:300, `GQ-17` at
docs/GRAPH_QUERY_SEMANTICS.md:330). When a survivor set exceeds the
Control-Plane-valued cap (D-10; ``survivor_cap``, default ``None`` = no cap),
the segment runs in-process instead of pushing — semantically identical and
free, per `GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342. This stage is
principal-agnostic, which is exactly why memoizing it is sound (D-IMPL-36, I.1
scope: per-execution only).

The registry, the ordering rule, and the composite-operator algebra live in
:mod:`ccf.operators` rather than here. The engine is the thing that *runs* a
plan; it is not the thing that decides what a plan is, and keeping the two
apart is what lets the composition-preservation harness assert against the
same composition path the engine takes.

**Stage 2 — what that truth means here.** Π is invoked over the composed view
with the intermediates and the perspective. Principal-conditioned, stateless.

**The engine-resolved operator set is the engine's own record of what ran.** It
is built from execution, not copied from the plan's declaration, which is what
makes the L6 lineage strict-equality gate a real comparison rather than a
tautology (INV-CH7-47).

The registry is populated by explicit boot-time ``register`` calls at the
composition root (D-IMPL-37 — no import-side-effect registration in v0), and a
duplicate key is a boot failure rather than a runtime surprise (INV-CH7-29).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    GraphQuery,
    GraphReader,
    GraphView,
    SnapshotPinnable,
    SourceAttestation,
    StoreSnapshotPin,
)
from ccf.operators.base import OperatorOutput, OperatorProvenance
from ccf.operators.planner import IntermediateCache, build_operator_plan
from ccf.products.contract import RegisteredProductClass
from ccf.products.gates import AttestationRefusal, refuse_attestation
from ccf.projection.segmentation import (
    PushableSegment,
    compile_segment_query,
    segment_plan,
)
from ccf.operators.registry import (
    DuplicateOperatorKey,
    OperatorRegistry,
    UnregisteredOperator,
)
from ccf.projection.acquisition import (
    AcquiredContent,
    AcquirerNotConfigured,
    ContentAcquirer,
    ContentAcquiringPlan,
    ContentUnsatisfied,
    UndeclaredAcquisition,
)
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan

__ccf_mode__ = "algorithmic"

__all__ = [
    "AcquirerNotConfigured",
    "ContentUnsatisfied",
    "DuplicateOperatorKey",
    "ExecutionResult",
    "ExecutionStep",
    "OperatorRegistry",
    "ProjectionEngine",
    "UndeclaredAcquisition",
    "UnregisteredOperator",
]


class ExecutionStep(CCFContract):
    """One executed stage of the operator plan, in execution order.

    Lands verbatim in replay dimension 5 (Content Generation Path): the
    sequence of steps *is* how the product came to be, and a record that named
    only the operators without their order could not distinguish a
    Policy-before-Similarity run from the forbidden inverse.
    """

    operator_key: str
    category: str
    parameter_hash: str


class ExecutionResult(CCFContract):
    """Everything one two-stage execution produced.

    Attributes:
        plan_id: Identity of the projection that ran.
        operators_invoked: The **engine-resolved** operator set — what ran, as
            observed by the thing that ran it.
        steps: Execution order, for replay dimension 5.
        provenance: Provenance chain of the final intermediate, or ``None``
            when the plan declared no operators. ``None`` rather than an empty
            chain: the empty-operator guard exists precisely to refuse this
            case at L6, and papering over it here would remove its subject.
        projection: Π's output.
        view: The final composed view. Retained because the snapshot watermark
            and touched-substate manifest of replay dimension 1 are computed
            from it (D-IMPL-06 — a logical snapshot, never a physical copy).
        acquisitions: Content acquired at decision time, in resolution order,
            each with its content address. Empty for a plan that declared none.
            This is replay dimension 5's record of what the interpretation read
            from outside the graph: **a replay re-feeds these recorded items
            rather than re-acquiring** (INV-CH7-31), because a remote resource
            that moved between the decision and the replay would otherwise make
            the replay a new decision wearing the old one's identifier.
        executed_queries: The ``GraphQuery`` values the segmented loop issued,
            **in execution order** — appended at each ``reader.query()`` call
            site, never predicted from the plan, so the sequence records what
            ran (`GQ-20` at docs/GRAPH_QUERY_SEMANTICS.md:391). A cap firing
            is visible here as an absent entry (`GQ-18` at
            docs/GRAPH_QUERY_SEMANTICS.md:342). Sentinel-defaulted to the
            empty tuple. :func:`~ccf.replay.record.build_replay_record`
            threads the per-round-trip ``content_hash`` pins from this field
            into replay dimension 5 (D-11), and the serve seam persists the
            values' canonical bytes (:class:`~ccf.replay.serve.QueryPinWriter`)
            — the queries travel here as **values, not only hashes**, so the
            serving path can store the literal question an auditor will ask
            for.
        survivor_cap: The cap value **in force for this execution** — the
            engine's constructor value, echoed onto the result so the
            execution facts carry it to
            :func:`~ccf.replay.record.build_replay_record`, which pins it
            into replay dimension 2 (D-10). ``None`` is the positive no-cap
            posture. Recorded whether or not any segment's survivor count
            ever reached it: the dimension-2 fact is the configuration the
            decision ran under, not whether it fired — the firing is visible
            in ``executed_queries``.
        source_attestation: The source's
            :class:`~ccf.graph.protocols.SourceAttestation` **as observed at
            the read seam**, threaded here unconditionally by
            :meth:`ProjectionEngine.execute` — even an execution whose
            caller skipped :meth:`ProjectionEngine.check_source_attestation`
            carries the provenance posture it read under, which is what
            makes the ungoverned path repudiation-proof (T-15.2-25) and what
            the additive gate in :func:`~ccf.products.gates.run_gates`
            refuses on. ``None`` is the positive assertion that the reader
            reported no attestation — an execution driven against a
            pre-phase reader that predates the ``attestation`` property, or
            a result built by hand without the field — and passes the gate:
            the compatibility posture (D-09).
            :func:`~ccf.replay.record.build_replay_record` pins this value
            into replay dimension 1.
        store_snapshot_pin: The substrate's transaction-time head **as read
            once before the first query of this execution** (ledger row
            24.5-L-02, D-IMPL-240): a fact about the read, so it is taken
            before anything is read — a pin taken afterward would describe
            whatever head the store had reached by then, not the state the
            queries saw. Threaded unconditionally by
            :meth:`ProjectionEngine.execute` from a reader that is
            :class:`~ccf.graph.protocols.SnapshotPinnable`;
            :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN` is the positive
            assertion that the reader exposes no native pin — every reader
            shipped before the Protocol existed, and a result built by hand
            without the field. The resolver copies it onto
            :attr:`~ccf.products.contract.ProductLineage.store_snapshot_pin`
            and :func:`~ccf.replay.record.build_replay_record` pins it into
            replay dimension 1, where replay resolves exactly it or refuses.
        empty_results: The operator keys whose output view carried zero
            entities AND zero relationships (ledger row ``24.5-L-24``) —
            the Standard's *an operator returned an empty set*, observed by
            the thing that ran it. Computed ALWAYS by
            :meth:`ProjectionEngine.execute`, one inspection of each
            operator's :class:`~ccf.operators.base.OperatorOutput` view as
            it is produced, so the empty set is the engine's positive
            assertion *no operator returned empty* and not a sentinel for
            absence — an engine execution always observes this. The
            governed resolver threads it to
            :func:`~ccf.products.gates.run_gates` as ``empty_results``,
            where the second half of the empty-operator gate
            (:data:`~ccf.products.gates.GATE_EMPTY_OPERATOR_RESULT`) refuses
            a non-empty set by name; a result built by hand without the
            field carries the empty set and passes.
    """

    plan_id: str
    operators_invoked: frozenset[str]
    steps: tuple[ExecutionStep, ...]
    provenance: OperatorProvenance | None
    projection: ProjectionOutput
    view: GraphView
    acquisitions: tuple[AcquiredContent, ...] = ()
    executed_queries: tuple[GraphQuery, ...] = ()
    survivor_cap: int | None = None
    source_attestation: SourceAttestation | None = None
    store_snapshot_pin: StoreSnapshotPin = NO_STORE_SNAPSHOT_PIN
    empty_results: frozenset[str] = frozenset()

    def touched_entities(self) -> tuple[str, ...]:
        """Entity URIs the execution actually touched, sorted."""
        return tuple(sorted(record.claim.entity_uri for record in self.view.entities))

    def touched_relationships(self) -> tuple[str, ...]:
        """Relationship keys the execution actually touched, sorted."""
        return tuple(sorted(edge.relationship_key for edge in self.view.relationships))

    def state_watermark(self) -> str:
        """Content address of the composed view — the store-state watermark.

        D-IMPL-06: the snapshot is logical. This hash plus the tenant, the
        temporal boundary, and the touched-substate manifest identify the graph
        state a decision was made against, without copying a byte of it.
        """
        return content_hash(self.view)


class ProjectionEngine:
    """Runs the operator plan, then decision-time acquisition, then Π.

    Args:
        reader: Read-only graph access. There is no writer parameter on this
            constructor, and that absence is the point — L4/L5 are structurally
            incapable of writing (INV-CH7-11, single-writer per CLAUDE.md §10).
            Adding an acquirer does not change this: an acquirer holds no graph
            handle either, and what it fetches terminates in the projection
            payload rather than entering L3.
        registry: The boot-populated operator registry.
        acquirer: Resolves the content a :class:`ContentAcquiringPlan` declares
            (CLAUDE.md §7.1, whitepaper §6.6). Optional, and its optionality is
            structural rather than convenient: **a replay constructs the engine
            without one** and re-feeds the recorded acquisitions, so an engine
            that could always reach the network would make replay a live call.
        survivor_cap: The survivor-set size cap of `GQ-18` at
            docs/GRAPH_QUERY_SEMANTICS.md:342 (D-10). **Mechanism only** —
            the value is Control Plane configuration, and the default is
            ``None`` = no cap, the SDK's posture: a threshold constant in
            ``/src`` would be a domain value (CLAUDE.md §11). When a
            post-in-process segment's survivor count exceeds the cap, the
            engine runs that segment's operators in-process over the
            surviving view instead of pushing — always sound, no extra
            substrate read, and visible in the executed query sequence.
            Plan 15.2-08 wires the deployment-manifest field and pins the
            value in force into replay dimension 2.
    """

    def __init__(
        self,
        *,
        reader: GraphReader,
        registry: OperatorRegistry,
        acquirer: ContentAcquirer | None = None,
        survivor_cap: int | None = None,
    ) -> None:
        self._reader = reader
        self._registry = registry
        self._acquirer = acquirer
        self._survivor_cap = survivor_cap
        self._last_survivor_set_sizes: tuple[int, ...] = ()

    @property
    def last_survivor_set_sizes(self) -> tuple[int, ...]:
        """Survivor-set sizes at each in-process → pushable boundary — telemetry.

        The D-10 locked sub-clause ("pushed-vs-scanned telemetry additionally
        reports set sizes"), implemented at the engine because the survivor
        set exists only here: a capped segment issues no query, so a
        reader-level counter could never observe it. One entry per
        in-process → pushable segment boundary of the **most recent**
        :meth:`execute`, in execution order, recorded whether the following
        segment pushed or the cap ran it in-process — the size is the same
        number either way; which happened is visible in the query count of
        ``ExecutionResult.executed_queries``. Empty before the first
        ``execute()`` and for plans with no such boundary (no-Similarity and
        fully-pushable plans).

        Three deliberate postures:

        * **Per-execution, reset at each ``execute()`` start** — a contrast
          with the monotonic per-instance
          :attr:`ccf.graph.reader.BaseGraphReader.translated_answers` /
          :attr:`ccf.graph.reader.BaseGraphReader.fallback_answers`
          counters: those attribute answers over a reader's lifetime; this
          reports one execution's boundaries, replaced (never appended to)
          by the next.
        * **Outside the replay record** — performance is never a replay
          input (D-04, `GQ-34` at docs/GRAPH_QUERY_SEMANTICS.md:609); the
          plan 15.2-08 no-telemetry pin covers this field too.
        * **Report-only** — no threshold logic and no comparison against
          ``survivor_cap`` lives here (mechanism, not values, CLAUDE.md
          §11); the cap decision happens only at the segment decision point
          inside :meth:`execute`.
        """
        return self._last_survivor_set_sizes

    def _reader_attestation(self) -> SourceAttestation | None:
        """The reader's attestation, or ``None`` for a pre-phase reader.

        Tolerant by design, and the tolerance is the compatibility promise:
        a user-implemented reader written before the ``attestation``
        property existed still conforms to every obligation it was written
        against, and an engine that crashed on it would be a behavior break
        this phase forbids. Such a reader yields ``None`` — which the
        additive gate passes and replay dimension 1 records as the positive
        "no attestation was reported" claim (D-09).
        """
        attestation = getattr(self._reader, "attestation", None)
        if attestation is None or isinstance(attestation, SourceAttestation):
            return attestation
        return None

    def _reader_snapshot_pin(self) -> StoreSnapshotPin:
        """The reader's store-native head pin, or the sentinel for one that cannot pin.

        The pin analogue of :meth:`_reader_attestation` (ledger row
        24.5-L-02, D-IMPL-240), and tolerant for the same reason: pinning is
        a structural Protocol (:class:`~ccf.graph.protocols.SnapshotPinnable`),
        so a reader that does not implement it has nothing to add and an
        engine that crashed on it would be a behavior break. Such a reader
        yields :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN` — the
        positive claim "this substrate exposes no native pin" — and replay
        dimension 1 records exactly that.
        """
        if isinstance(self._reader, SnapshotPinnable):
            return self._reader.snapshot_pin()
        return NO_STORE_SNAPSHOT_PIN

    def check_source_attestation(
        self, *, product_class: RegisteredProductClass
    ) -> AttestationRefusal | None:
        """The caller-visible pre-execute attestation check (D-09) — SDK-defined.

        SDK-defined per CLAUDE.md §11, the early layer of the two-layer D-09
        enforcement. It compares this engine's reader's
        :attr:`~ccf.graph.protocols.GraphReader.attestation` — a property,
        so **zero queries are issued and no data moves** — against
        ``product_class``'s accepted-mode sets, and returns the refusal as a
        value, never an exception (the Phase 04 refusal-vs-exception line: a
        below-modes source is an expected governance outcome, not a broken
        deployment). The comparison itself is
        :func:`~ccf.products.gates.refuse_attestation`, the same function
        the gate path runs, so the two layers cannot disagree.

        Serving code calls this **before** :meth:`execute`, in the same
        match-composition the gates use::

            match engine.check_source_attestation(product_class=product_class):
                case None:
                    execution = engine.execute(plan=plan, ...)
                    gated = run_gates(
                        candidate,
                        engine_resolved=execution.operators_invoked,
                        now=now,
                        registry=registry,
                        product_class=product_class,
                        source_attestation=execution.source_attestation,
                    )
                case refusal:
                    ...  # a returned value naming the failing dimension

        The check is advisory in position but not in effect: a caller that
        skips it changes nothing structurally, because :meth:`execute` pins
        the attestation into the execution result unconditionally and
        :func:`~ccf.products.gates.run_gates` refuses a below-modes pin —
        :class:`~ccf.products.gates.ServableProduct` remains unconstructible
        for a below-accepted-modes source either way. What the pre-check
        buys is *earliness*: the refusal before the first byte moves.

        Returns:
            ``None`` when the source's modes are accepted (or the reader
            reports no attestation — the compatibility posture), otherwise
            the :class:`~ccf.products.gates.AttestationRefusal` naming the
            failing dimension.
        """
        return refuse_attestation(
            attestation=self._reader_attestation(), product_class=product_class
        )

    def _resolve_content(
        self,
        *,
        plan: ContentAcquiringPlan,
        tenant_id: str,
        recorded_acquisitions: tuple[AcquiredContent, ...] | None,
    ) -> tuple[AcquiredContent, ...]:
        """Resolve the plan's declared content, or refuse.

        Three refusals, no fallback. "Proceed without the content" is never one
        of the outcomes: a projection silently interpreting absent content it
        declared it needed is the debt-blind decision the fabric exists to
        prevent (whitepaper §7.7).
        """
        requests = plan.required_content()
        if recorded_acquisitions is not None:
            resolved: Mapping[str, AcquiredContent] = {
                acquired.request.request_key: acquired
                for acquired in recorded_acquisitions
            }
        elif self._acquirer is None:
            raise AcquirerNotConfigured(
                f"plan {plan.plan_id!r} declares "
                f"{len(requests)} content request(s) and this engine was "
                "constructed without an acquirer"
            )
        else:
            resolved = self._acquirer.acquire(
                requests=requests, tenant_id=tenant_id
            )

        declared = {request.request_key for request in requests}
        undeclared = sorted(set(resolved) - declared)
        if undeclared:
            raise UndeclaredAcquisition(
                f"plan {plan.plan_id!r} did not declare {undeclared}; the "
                "declared set and the resolved set are compared, never merged"
            )
        missing = sorted(declared - set(resolved))
        if missing:
            raise ContentUnsatisfied(
                f"plan {plan.plan_id!r} declared {missing}, which came back "
                "unsatisfied"
            )
        acquisitions = tuple(resolved[request.request_key] for request in requests)
        for acquired in acquisitions:
            if acquired.content_hash != acquired.rehash():
                raise ContentUnsatisfied(
                    f"content for {acquired.request.request_key!r} does not "
                    "match its recorded content address"
                )
        return acquisitions

    def execute(
        self,
        *,
        plan: ProjectionPlan | ContentAcquiringPlan,
        perspective: Perspective,
        tenant_id: str,
        temporal_boundary: datetime,
        seeds: frozenset[str] | None = None,
        recorded_acquisitions: tuple[AcquiredContent, ...] | None = None,
    ) -> ExecutionResult:
        """Execute ``plan`` for ``perspective`` as of ``temporal_boundary``.

        ``temporal_boundary`` is supplied by the caller and threaded into every
        operator and into every issued query's ``as_of``. Nothing in this path
        reads a clock (04-RESEARCH.md anti-patterns): a replay feeds the
        boundary the original decision used and gets the original answer.

        **The segmented loop** (`GQ-14` at docs/GRAPH_QUERY_SEMANTICS.md:289).
        The plan splits into the pushed/in-process alternation and the engine
        issues one ``reader.query()`` per pushed segment, appending each query
        to the executed sequence **at the call site** — execution order, what
        ran, never what the plan predicted (`GQ-20` at
        docs/GRAPH_QUERY_SEMANTICS.md:391). A pushed segment's operators are
        re-applied over the segment's answer to derive execution-side
        provenance; the re-application is guaranteed to reproduce the answer
        because the answer is a fixed point of its own operators (`GQ-19` at
        docs/GRAPH_QUERY_SEMANTICS.md:356). After each in-process segment the
        surviving entity URIs become the next pushed segment's
        ``allowed_entities`` (`GQ-17` at docs/GRAPH_QUERY_SEMANTICS.md:330);
        when the survivor count exceeds ``survivor_cap`` (D-10, Control
        Plane-valued), that segment runs in-process over the surviving view
        instead — no query issued, byte-identical by `GQ-18` at
        docs/GRAPH_QUERY_SEMANTICS.md:342.

        **Stage order is load-bearing.** Acquisition runs *after* the operator
        plan and *before* Π. Policy is an operator, so by the time anything is
        fetched the view has already been constrained for this principal, and
        nothing is acquired on behalf of a principal Policy excluded — the
        INV-CH7-26 ordering argument applied to acquisition. Running the fetch
        first would be cheaper and would be exactly wrong. Segmentation is
        internal to the operator stage and does not reorder around it.

        **The caller's walk starting points** (D-IMPL-111 limb (a), Dave,
        2026-08-11). ``seeds`` is where the *question* says the walk begins —
        in the shipped path, the entity anchor of the
        :class:`~ccf.products.request.ProductRequest` the caller asked, derived
        by the single :func:`~ccf.products.request.request_seeds` reading. It
        reaches **every pushable segment that carries a traverse family, and no
        other**, because `GQ-03` at docs/GRAPH_QUERY_SEMANTICS.md:87 refuses
        seeds with no walk to start: a plan whose segment walks nothing is
        passed ``None`` rather than made unconstructible by the caller's
        question. Which segment that is, is a property of the plan — in the
        shipped reference example the traverse family lands in a *post*-
        in-process segment, so a rule that seeded only the opening segment
        would have seeded nothing at all.

        **The anchor and the survivor set compose rather than compete.**
        `GQ-17` at docs/GRAPH_QUERY_SEMANTICS.md:330 already fixes the
        interaction: explicit seeds are intersected with the in-scope state, so
        an anchor that did not survive the preceding segment starts no walk,
        and the walk still may not cross outside the survivor set. This is
        **not** the case
        :func:`~ccf.projection.segmentation.compile_segment_query` refuses —
        that refusal is about promoting *survivors* to walk starts, which would
        make the walk begin everywhere the previous segment left something
        standing. The caller's anchor is one named entity, stated in the
        question rather than produced by a segment.

        Seeds **widen** rather than narrow: `GQ-11` unions them into the
        frontier the ``seed_entity_classes`` selection produced. That is a
        change to *which view* the operators are handed, never to what an
        operator computes over the view it is handed, so
        composition-preservation ``(A∘B)(G) = A(B(G))`` is untouched — it is a
        property of the operators, quantified over every view (CLAUDE.md §11).

        Args:
            seeds: Explicit walk starting points, ``None`` for "the plan's own
                seed classes and nothing else" — the pre-D-IMPL-111 posture and
                what every replay of a record carrying no request runs under.
            recorded_acquisitions: Content a prior execution recorded. Supplied
                by a replay, which re-feeds rather than re-acquires
                (INV-CH7-31); when present the acquirer is not called at all.

        Raises:
            UnregisteredOperator: the plan declared a key the registry does not
                hold.
            AcquirerNotConfigured: the plan declares content and neither an
                acquirer nor recorded acquisitions were supplied.
            UndeclaredAcquisition: content came back that the plan never
                declared.
            ContentUnsatisfied: a declared request came back unsatisfied, or a
                re-fed item does not match its recorded content address.
        """
        operator_plan = build_operator_plan(
            registry=self._registry, required_operators=plan.required_operators()
        )
        segmented = segment_plan(operator_plan.operators)
        operators_by_key = {
            operator.key: operator for operator in operator_plan.operators
        }
        cache = IntermediateCache()
        outputs: dict[str, OperatorOutput] = {}
        steps: list[ExecutionStep] = []
        chain: tuple[OperatorProvenance, ...] = ()
        executed_queries: list[GraphQuery] = []
        survivor_sizes: list[int] = []
        # 24.5-L-24: the operator keys whose output carried nothing — read
        # off each OperatorOutput once, as it is produced, never off the
        # payload. Always computed; the empty set is a positive assertion.
        empty_results: set[str] = set()
        self._last_survivor_set_sizes = ()
        survivors: frozenset[str] | None = None
        view: GraphView | None = None
        # Read ONCE, before the first ``reader.query()`` of this execution
        # (24.5-L-02): the pin is a fact about the read, and a pin taken
        # after the queries would describe a later head, not the state the
        # queries saw. The sentinel for a reader that cannot pin.
        store_snapshot_pin = self._reader_snapshot_pin()

        def run_operators(
            operator_keys: tuple[str, ...], current: GraphView
        ) -> GraphView:
            """Run one segment's operators over ``current``, recording what ran."""
            nonlocal chain
            for key in operator_keys:
                operator = operators_by_key[key]
                output = cache.run(
                    operator,
                    view=current,
                    tenant_id=tenant_id,
                    temporal_boundary=temporal_boundary,
                    upstream=chain,
                )
                current = output.view
                outputs[operator.key] = output
                if not output.view.entities and not output.view.relationships:
                    empty_results.add(operator.key)
                chain = (output.provenance,)
                steps.append(
                    ExecutionStep(
                        operator_key=operator.key,
                        category=operator.category,
                        parameter_hash=output.provenance.parameter_hash,
                    )
                )
            return current

        for segment in segmented.segments:
            if isinstance(segment, PushableSegment):
                if survivors is not None:
                    # The D-10 set-size report: one entry per in-process →
                    # pushable boundary, whether or not the cap fires below.
                    survivor_sizes.append(len(survivors))
                    self._last_survivor_set_sizes = tuple(survivor_sizes)
                if (
                    survivors is not None
                    and self._survivor_cap is not None
                    and len(survivors) > self._survivor_cap
                ):
                    # GQ-18: above cap the segment runs in-process over the
                    # surviving view — no query issued, nothing appended; the
                    # executed sequence shows what ran.
                    assert view is not None  # noqa: S101 - survivors imply a prior view
                    view = run_operators(segment.operator_keys, view)
                else:
                    # D-IMPL-111 limb (a): the question's anchor starts the
                    # walk, on every segment that walks and on no segment that
                    # does not (`GQ-03` refuses seeds with no walk to start).
                    # Where a survivor set is also in force the two compose
                    # under `GQ-17` — the anchor starts a walk only if it
                    # survived, and the walk still may not cross outside the
                    # set.
                    query = compile_segment_query(
                        segment,
                        tenant_id=tenant_id,
                        as_of=temporal_boundary,
                        seeds=(
                            seeds
                            if any(
                                fragment.traverse is not None
                                for fragment in segment.fragments
                            )
                            else None
                        ),
                        allowed_entities=survivors,
                    )
                    view = self._reader.query(query)
                    # Appended at the call site: execution order, never
                    # plan-side prediction (GQ-20).
                    executed_queries.append(query)
                    view = run_operators(segment.operator_keys, view)
            else:
                assert view is not None  # noqa: S101 - segments open with a pushable segment
                view = run_operators(segment.operator_keys, view)
                survivors = frozenset(
                    record.claim.entity_uri for record in view.entities
                )

        assert view is not None  # noqa: S101 - the opening segment always produced a view

        acquisitions: tuple[AcquiredContent, ...] = ()
        if isinstance(plan, ContentAcquiringPlan):
            acquisitions = self._resolve_content(
                plan=plan,
                tenant_id=tenant_id,
                recorded_acquisitions=recorded_acquisitions,
            )
            projection = plan.invoke(
                view=view,
                operator_outputs=outputs,
                perspective=perspective,
                temporal_boundary=temporal_boundary,
                acquired_content={
                    acquired.request.request_key: acquired
                    for acquired in acquisitions
                },
            )
        else:
            projection = plan.invoke(
                view=view,
                operator_outputs=outputs,
                perspective=perspective,
                temporal_boundary=temporal_boundary,
            )
        return ExecutionResult(
            plan_id=plan.plan_id,
            operators_invoked=frozenset(outputs),
            steps=tuple(steps),
            provenance=chain[0] if chain else None,
            projection=projection,
            view=view,
            acquisitions=acquisitions,
            executed_queries=tuple(executed_queries),
            survivor_cap=self._survivor_cap,
            # Unconditional: even a caller that skipped the pre-check leaves
            # the provenance posture it read under in the execution facts,
            # which run_gates then refuses on and replay dimension 1 pins
            # (D-09; T-15.2-25).
            source_attestation=self._reader_attestation(),
            # The head read before the first query, not re-read here: a
            # second read could report a head the queries never saw.
            store_snapshot_pin=store_snapshot_pin,
            empty_results=frozenset(empty_results),
        )
