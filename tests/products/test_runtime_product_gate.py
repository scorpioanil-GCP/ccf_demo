"""`R-11` — a product class's own declared invariant, running on the governed path.

`24.10-02`. The ruling of record is ``D-IMPL-282`` ``R-11`` option 1a (Dave,
2026-09-08) and its boundary sentence: *"the runtime gate is not a new
universal policy vocabulary. It is a declared product invariant with a governed
identity, whose implementation is supplied by the deployment. It executes after
candidate construction and before fitness/fulfillment. Replay should be able to
say which gate ran and, if it refused, which gate produced the refusal."*

**Where the arithmetic comes from, and where it does not.** The predicate
exercised here reproduces
``examples/cp-05-credit-exposure-rollup/assembler.py::reconciliation_guard``
— *"Gross must be >= guarantee-adjusted, per group. Adjusted exposure exceeding
gross is arithmetically impossible; if it happens, step 5.2 removed the same
exposure twice. … The other three gates catch a broken pipeline. This one
catches a PLAUSIBLE WRONG ANSWER."* cp-05 was **read** under the Phase 24.10
boundary (*"No cp-05 source, transcript, expected artifact, or published page
is modified during Phase 24.10; cp-05 declarations and measured estate behavior
may be used as test inputs to prove the SDK changes"*) and is **not imported**:
the predicate is rewritten in this harness, and the two figures below are
transcribed from cp-05's shipped transcript as test inputs. cp-05 is not
rewired here; that is the post-phase adoption step.

The six behaviors, and why each is worth a test rather than a docstring:

1. **The guard fires.** A rollup whose adjusted committed exceeds its gross is
   refused, as a governed refusal of the new kind rather than an exception out
   of a deployment's spine.
2. **The guard does not fire on cp-05's shipped figures.** The positive
   control, and it is not optional: a gate observed only in its firing state is
   a gate that might be refusing everything.
3. **`D-14`, the refusal half.** The record persisted by (1) is read back out
   of the artifact store and names the gate and its lane — asserted against the
   **stored bytes**, never against the value the resolver returned in memory.
4. **The gate does not run when the universal gates refused.** There is no
   candidate to hold an invariant against, proved with a counting gate.
5. **The gate runs before fitness.** A candidate that both violates the
   invariant and exceeds its applicable tolerance yields the product-invariant
   refusal, not the tolerance one — `D-12`'s ordering observed rather than
   asserted in a comment.
6. **`D-14`, the admitted half.** The served determination's record pins a
   class and a lane; the ``ProductClassDeclaration`` resolved at that pinned
   pair names the gate that ran.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    PRODUCT_CLASS as PRODUCT_CLASS_ARTIFACT,
)
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.refusal import NO_REPLAY_REFERENCE, RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import ARTIFACT_SET, PRODUCT_CLASS_KEY
from tests.products.test_resolver_seam import (
    ASKED_AT,
    MAX_TTL_SECONDS,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_DOCUMENT,
    THRESHOLD_PARAMETER,
    _ask,
    _Booted,
    _boot,
    _request,
    _resolver,
)
from tests.composition import register_typed_at_composition

# --- the deployment's own vocabulary ----------------------------------------
#
# Test-side values, never SDK values (CINV-01). The gate's id and lane are the
# DEPLOYMENT's to author; nothing in `src/` spells either.

#: The invariant this fixture deployment declares, and the lane it declares it
#: at. cp-05 calls its own *"the fourth validation gate"*; this harness names it
#: after what it reconciles.
GATE_ID = "fixture.reconciliation-guard"
GATE_VERSION = "1.0.0"

#: A SECOND lane of the same declaration, carrying a different gate id. It
#: exists only so test 6's resolution can be shown to resolve at the version
#: the record pinned rather than at the latest one — a resolution that read
#: "latest" would pass against one declaration and be wrong the first time a
#: deployment revised its gate.
LATER_PRODUCT_VERSION = "2.0.0"
LATER_GATE_ID = "fixture.reconciliation-guard-revised"

#: cp-05's shipped figures, transcribed from
#: `examples/cp-05-credit-exposure-rollup/page/run-transcript.txt` lines 15-16
#: (read, never edited). They are the NOT-firing control: gross exceeds
#: adjusted by the 800,000,000 the guarantee dedup removed, which is the
#: arithmetic the guard exists to protect.
CP05_GROSS_COMMITTED = 10_125_000_000
CP05_ADJUSTED_COMMITTED = 9_325_000_000

#: The plausible wrong answer. The same adjusted figure against a gross from
#: which the guarantee dedup was ALSO subtracted — cp-05's *"step 5.2 removed
#: the same exposure twice"*. Nothing in the output looks broken: it is a
#: well-formed rollup with two large numbers in it, and only the invariant
#: says which way round they must be.
DOUBLE_SUBTRACTED_GROSS = CP05_ADJUSTED_COMMITTED - 800_000_000

#: The class's declared default tolerance for the fitness leg of test 5, and
#: the debt the fixture scorer reports there. Two fixture numbers, authored
#: here and nowhere in `src/`; the second exceeds the first, which is the whole
#: point of the pair.
DECLARED_TOLERANCE = "0.5"
DEBT_OVER_TOLERANCE = "0.9"

#: The payload members the rollup carries. Named once so the projection and the
#: guard cannot come apart into two spellings of one contract.
GROSS = "gross"
ADJUSTED = "adjusted"
COMMITTED = "committed"


# --- the deployment's Π, its scorer, and its gate ----------------------------


class _RollupProjection:
    """A projection emitting a two-sided rollup, cp-05's shape and not its data."""

    def __init__(
        self, *, required: tuple[str, ...], request: ProductRequest, gross: int
    ) -> None:
        self._required = required
        self._request = request
        self._gross = gross

    @property
    def plan_id(self) -> str:
        return PRODUCT_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                GROSS: {COMMITTED: self._gross},
                ADJUSTED: {COMMITTED: CP05_ADJUSTED_COMMITTED},
                "assembled": len(list(view.entities)),
            },
        )


def _rollup_factory(gross: int) -> Any:
    """A conforming plan factory emitting a rollup with ``gross`` on one side."""

    def factory(*, required: tuple[str, ...], request: ProductRequest) -> Any:
        return _RollupProjection(required=required, request=request, gross=gross)

    return factory


def _scorer_reporting(debt: str) -> Any:
    """A fixture debt scorer reporting one figure. Deployment policy, not SDK."""

    def scorer(
        *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        return DebtAssessment(
            debt=Decimal(debt),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
            scorers=(),
        )

    return scorer


class _CountingGuard:
    """cp-05's reconciliation guard, rewritten here, counting its own calls.

    The count is what makes tests 1, 2 and 4 non-vacuous in three different
    directions: a resolver that never called the gate would satisfy every
    assertion about a gate that admits, and one that called it twice would
    produce two refusal records for one determination.
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(
        self,
        *,
        candidate: ContextProductContract,
        evidence: ExecutionEvidence | None = None,
    ) -> str | None:
        self.calls += 1
        gross = int(candidate.payload[GROSS][COMMITTED])
        adjusted = int(candidate.payload[ADJUSTED][COMMITTED])
        if adjusted > gross:
            return (
                f"reconciliation guard: adjusted committed {adjusted} exceeds"
                f" gross {gross}. The dedup logic double-subtracted."
            )
        return None


# --- the deployment that DECLARES the invariant ------------------------------


def _declaring_document(
    *,
    schema_version: str = PRODUCT_VERSION,
    gate_id: str = GATE_ID,
    tolerance: str | None = None,
) -> dict[str, Any]:
    """The fixture class document with a ``declared_product_gate`` block."""
    document = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    document["schema_version"] = schema_version
    document["declared_product_gate"] = {
        "gate_id": gate_id,
        "gate_version": GATE_VERSION,
    }
    if tolerance is not None:
        document["serve_obligations"] = {"default_debt_tolerance": tolerance}
    return document


@pytest.fixture()
def declaring(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The fixture deployment, with its class DECLARING the runtime invariant."""
    yield from _boot(tmp_path, product_class=_declaring_document())


@pytest.fixture()
def declaring_with_tolerance(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same, plus a declared default tolerance and the request argument.

    Test 5 needs a determination that is wrong AND unfit at once, so both
    authorities have to be live: the class declares the default and the request
    contract declares the Standard's universal ``debt_tolerance`` argument, or
    the tolerance never reaches a resolution at all.
    """
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DEBT_TOLERANCE_PARAMETER
    ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    yield from _boot(
        tmp_path,
        product_class=_declaring_document(tolerance=DECLARED_TOLERANCE),
        request_contract=request_contract,
    )


def _gated_resolver(
    booted: _Booted, *, gross: int, guard: _CountingGuard, **overrides: Any
) -> Any:
    """The wiring under test: the deployment's Π, and its gate on the seam."""
    return _resolver(
        booted,
        plan_factory=_rollup_factory(gross),
        product_gate=guard,
        **overrides,
    )


def _record_at(booted: _Booted, uri: str) -> DecisionReplayRecord:
    """The record a reference resolves to, read back out of the STORE.

    Resolution is itself the assertion: the store refuses to hand back bytes
    that do not hash to the address asked for, so a returned record is also the
    claim that nothing changed between the append and this read.
    """
    return DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=booted.store.resolve_uri(uri=uri))
    )


def _declaration_at(
    booted: _Booted, *, schema_name: str, schema_version: str
) -> ProductClassDeclaration:
    """The class declaration at ONE pinned lane, resolved from the Control Plane.

    Walks the registry the resolver itself read from — ``keys_of_class`` then
    ``versions`` then ``peek``, the read surface
    :class:`~ccf.products.constraints.ReferencePolicyConstraintResolver` uses to
    answer *what was in force* — and selects on the pinned
    ``(schema_name, schema_version)`` pair rather than taking the latest
    registration. Reading "latest" is exactly the replay-determinism failure
    CLAUDE.md §7.4 forbids: *"Replay resolves exact artifact versions, never
    'latest'."*

    Exactly one match is required. A pinned pair that resolved to two
    declarations would mean replay could not say which one governed, and
    picking either would be the resolution inventing an answer.
    """
    registry = booted.control_plane
    found: list[ProductClassDeclaration] = []
    for key in registry.keys_of_class(PRODUCT_CLASS_ARTIFACT.class_id):
        for version in registry.versions(key):
            artifact = registry.peek(key, version)
            if not isinstance(artifact, ProductClassDeclaration):
                continue
            if (
                artifact.schema_name == schema_name
                and artifact.schema_version == schema_version
            ):
                found.append(artifact)
    assert len(found) == 1, (
        f"{schema_name}@{schema_version} resolved to {len(found)} declarations;"
        " a pinned pair that names none or several cannot answer which gate ran"
    )
    return found[0]


# --- 1. the guard fires ------------------------------------------------------


def test_the_guard_refuses_a_rollup_whose_adjusted_exceeds_its_gross(
    declaring: _Booted,
) -> None:
    """The plausible wrong answer, caught on the governed path.

    Not an exception out of a deployment's spine: a governed refusal of a kind
    the audit vocabulary names, carrying the declared identity the resolver
    stamped from the Control Plane.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(declaring, gross=DOUBLE_SUBTRACTED_GROSS, guard=guard),
        _request(),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-invariant-refusal"
    assert guard.calls == 1, "the gate runs exactly once per determination"

    # The identity is the CONTROL PLANE's, and the resolver stamped it: the
    # callable returned only a detail string. The gate id crosses at every
    # disclosure level, because a consumer that cannot name the kind and its
    # reason cannot audit the refusal at all.
    assert outcome.reason == GATE_ID

    # The LANE does not cross at `minimal`, and its key is still present: a
    # gate version is not something a caller can act on, so
    # `PERMITTED_AT_MINIMAL` withholds it while preserving field presence
    # (`D-IMPL-253` amendment 2 (4)). `D-14` is discharged in the RECORD, which
    # is what test 3 reads. Asserted rather than skipped, so a later widening of
    # that table is a visible change here rather than a silent one.
    assert set(outcome.fields) == {"gate_version"}
    assert outcome.fields["gate_version"] == '"undisclosed"'
    assert outcome.disclosure == "minimal"


# --- 2. the guard does not fire on cp-05's shipped figures -------------------


def test_the_guard_admits_cp05s_shipped_figures(declaring: _Booted) -> None:
    """The positive control, and it is not optional.

    A gate observed only in its firing state is a gate that might be refusing
    everything, which would pass test 1 and be worthless. The figures are
    cp-05's own measured output — gross 10,125,000,000 against adjusted
    9,325,000,000, the 800,000,000 guarantee dedup between them — so what is
    measured here is the boundary rather than a wall.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(declaring, gross=CP05_GROSS_COMMITTED, guard=guard),
        _request(),
    )

    assert isinstance(outcome, ServedProduct)
    assert guard.calls == 1
    assert outcome.product.payload[GROSS][COMMITTED] == CP05_GROSS_COMMITTED
    assert outcome.product.payload[ADJUSTED][COMMITTED] == CP05_ADJUSTED_COMMITTED


# --- 3. D-14, the refusal half: replay names which gate refused --------------


def test_the_persisted_record_names_the_gate_that_refused(
    declaring: _Booted,
) -> None:
    """``D-14``: *"if it refused, which gate produced the refusal."*

    Asserted against the STORED BYTES rather than the value the resolver
    returned in memory. An in-memory assertion would pass against a resolver
    that built a correct refusal and recorded a different one, which is the
    audit failure this row exists to make impossible.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(declaring, gross=DOUBLE_SUBTRACTED_GROSS, guard=guard),
        _request(),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.replay_reference != NO_REPLAY_REFERENCE

    record = _record_at(declaring, outcome.replay_reference)
    recorded = RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )

    assert recorded.kind == "product-invariant-refusal"
    assert recorded.reason == GATE_ID
    assert recorded.fields["gate_version"] == f'"{GATE_VERSION}"'
    # The detail is the deployment's own sentence, carried whole into the
    # record: an examiner learns what the invariant said, not just that one
    # refused.
    assert str(DOUBLE_SUBTRACTED_GROSS) in recorded.detail
    assert str(CP05_ADJUSTED_COMMITTED) in recorded.detail


# --- 4. the gate does not run when the universal gates refused ---------------


def test_the_gate_never_runs_on_a_candidate_the_universal_gates_refused(
    declaring: _Booted,
) -> None:
    """There is no product to hold an invariant against.

    The TTL gate refuses first — a product lifetime above the registered
    ceiling — and the counting guard proves the deployment's predicate was
    never reached. A resolver that ran it anyway would be asking a product
    class about a product that does not exist.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(
            declaring,
            gross=DOUBLE_SUBTRACTED_GROSS,
            guard=guard,
            product_ttl_seconds=MAX_TTL_SECONDS + 1,
        ),
        _request(),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "ttl-refusal", (
        "the universal gate must be the one that refused, or this test is"
        " measuring the wrong branch"
    )
    assert guard.calls == 0


# --- 5. the gate runs before fitness -----------------------------------------


def test_a_wrong_and_unfit_determination_reports_the_invariant_not_the_tolerance(
    declaring_with_tolerance: _Booted,
) -> None:
    """``D-12``'s ordering, observed rather than asserted in a comment.

    One candidate that is BOTH wrong (adjusted exceeds gross) and unfit (its
    ``D_c`` exceeds the class's declared default tolerance). The refusal that
    comes back says which question the fabric answered first, and the ruling is
    that it answers *"is this right"* before *"is this fit"* — because
    reporting a wrong answer as merely stale would tell an examiner the
    opposite of what happened.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(
            declaring_with_tolerance,
            gross=DOUBLE_SUBTRACTED_GROSS,
            guard=guard,
            debt_scorer=_scorer_reporting(DEBT_OVER_TOLERANCE),
        ),
        _request(),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-invariant-refusal"
    assert guard.calls == 1


def test_the_ordering_control_reports_the_tolerance_when_the_answer_is_right(
    declaring_with_tolerance: _Booted,
) -> None:
    """CONTROL for test 5: the tolerance leg is live in this fixture.

    Without it, a fixture whose declared tolerance never bound anything would
    make the test above pass for the wrong reason — the invariant refusal would
    win because it was the only refusal available, not because it runs first.
    Same deployment, same scorer, cp-05's correct figures: the tolerance
    withholds.
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(
            declaring_with_tolerance,
            gross=CP05_GROSS_COMMITTED,
            guard=guard,
            debt_scorer=_scorer_reporting(DEBT_OVER_TOLERANCE),
        ),
        _request(),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "tolerance-exceeded"
    assert guard.calls == 1, (
        "the gate ADMITTED before the tolerance withheld — the order is the"
        " same in both legs and only the verdicts differ"
    )


# --- 6. D-14, the admitted half: replay names which gate RAN -----------------


def test_the_served_records_pinned_declaration_names_the_gate_that_ran(
    declaring: _Booted,
) -> None:
    """``D-14``: *"Replay should be able to say which gate ran."*

    **Why this shape and not a missing binding row.**
    ``GovernedResolver._applied_bindings`` emits rows for constraint artifacts,
    the request contract's own pin and a verified entitlement override; the
    product class declaration is deliberately not among them, and adding one
    would mint a second pin for a thing the record already pins. The gate
    identity is **declared** rather than per-determination, so pinning the
    declaration pins the gate, and *"which gate ran"* is answerable by
    construction through that resolution. This test walks the resolution so the
    claim is observed rather than reasoned about.

    The pin is read from ``record.content_generation_path.request`` — the
    question as asked, carrying ``schema_name`` and ``schema_version``, the
    class's own lane (INV-CH7-49).
    """
    guard = _CountingGuard()
    outcome = _ask(
        _gated_resolver(declaring, gross=CP05_GROSS_COMMITTED, guard=guard),
        _request(),
    )

    assert isinstance(outcome, ServedProduct)
    record = _record_at(declaring, outcome.replay_ref.uri)

    pinned = record.content_generation_path.request
    assert pinned is not None, (
        "a served record with no question recorded cannot pin a class lane,"
        " and the resolution below would have nothing to resolve at"
    )
    assert pinned.schema_name == PRODUCT_CLASS
    assert pinned.schema_version == PRODUCT_VERSION

    declaration = _declaration_at(
        declaring,
        schema_name=pinned.schema_name,
        schema_version=pinned.schema_version,
    )
    assert declaration.declared_product_gate.gate_id == GATE_ID
    assert declaration.declared_product_gate.gate_version == GATE_VERSION


def test_the_resolution_reads_the_pinned_lane_and_not_the_latest(
    declaring: _Booted,
) -> None:
    """CONTROL for test 6: *"latest"* would give a different, wrong answer.

    A second declaration is registered under the same Control Plane key at a
    different class lane, carrying a different gate id — a deployment revising
    its invariant. ``resolve_latest`` then names the revision, while the
    resolution at the pinned lane still names the gate the determination
    actually ran under. Without this control the walk above would pass on a
    deployment that only ever had one declaration, which is every deployment
    until the first revision.
    """
    later = ProductClassDeclaration.model_validate(
        _declaring_document(
            schema_version=LATER_PRODUCT_VERSION, gate_id=LATER_GATE_ID
        )
    )
    register_typed_at_composition(declaring.control_plane, 
        PRODUCT_CLASS_KEY, later, PRODUCT_CLASS_ARTIFACT
    )

    _latest_version, latest = declaring.control_plane.resolve_latest(
        PRODUCT_CLASS_KEY
    )
    assert isinstance(latest, ProductClassDeclaration)
    assert latest.declared_product_gate.gate_id == LATER_GATE_ID, (
        "the control is inert unless `latest` really is the revision"
    )

    at_the_pin = _declaration_at(
        declaring, schema_name=PRODUCT_CLASS, schema_version=PRODUCT_VERSION
    )
    assert at_the_pin.declared_product_gate.gate_id == GATE_ID


# --- the harness's own vacuity guards ----------------------------------------


def test_the_two_figures_are_cp05s_and_the_wrong_one_is_wrong() -> None:
    """The inputs mean what this module says they mean.

    Three facts, stated so a later edit to one constant cannot quietly turn the
    firing case into the admitting case or the reverse: cp-05's pair is
    ordered, the double-subtracted gross is not, and the gap between the two
    gross figures is the 800,000,000 the transcript attributes to the guarantee
    dedup.
    """
    assert CP05_GROSS_COMMITTED > CP05_ADJUSTED_COMMITTED
    assert CP05_ADJUSTED_COMMITTED > DOUBLE_SUBTRACTED_GROSS
    assert CP05_GROSS_COMMITTED - CP05_ADJUSTED_COMMITTED == 800_000_000
    assert CP05_ADJUSTED_COMMITTED - DOUBLE_SUBTRACTED_GROSS == 800_000_000


def test_the_guard_is_written_here_and_cp05_is_not_imported() -> None:
    """The phase boundary, held structurally rather than by intention.

    cp-05 is a **probe**, not a dependency (`D-IMPL-261`): importing its
    assembler would couple the SDK's own test suite to a frozen specimen and
    would make an SDK change look like an example failure. The predicate is
    rewritten above; only the figures and the arithmetic are borrowed.
    """
    import ast

    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert imported, "the walk found no imports, so it is measuring nothing"
    offenders = [name for name in imported if name.split(".")[0] == "examples"]
    assert not offenders, offenders


def test_the_asked_instant_is_data_and_not_a_clock() -> None:
    """Every determination in this module is asked as of a fixed instant.

    The property `ccf.products.request` exists to preserve, re-asserted here
    because a gate test that read a clock would replay differently tomorrow.
    """
    assert ASKED_AT == datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
    assert _request().asked_at == ASKED_AT
    assert THRESHOLD_PARAMETER in _request().parameters
