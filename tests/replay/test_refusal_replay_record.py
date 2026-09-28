"""``24.6-L-08`` — a refusal is a first-class, five-dimension replay decision.

Ruling of record: ``D-IMPL-253`` Q13, Dave, verbatim — *"Refusal is itself a
decision and deserves the same five-dimensional replay model. Do not create
second-class replay."* — with ``D-IMPL-256``'s delivery-boundary corollary,
*"No fulfilled Context Product does not mean no Decision Replay"*, and its
invariant: *"Every governed determination that crosses a CCF delivery boundary
— fulfilled or refused, tool or resource, authorized or denied — must reach the
replay writer before the response is released."*

**What was true before this row, and is the thing under test here.** Three of
the governed resolver's paths returned a refusal shell and appended nothing,
and :func:`~ccf.replay.record.build_replay_record` could not have written one
even had they tried: it required a ``product`` and read five dimension-5 values
off it. A question that produced no product produced no audit record at all.

Seven legs, each pinning a property the composition would lose if it moved:

(a) **A pre-assembly refusal is recorded, and dimension 1 says positively that
    nothing was read.** Not an empty watermark, which would claim the graph was
    read and found empty — a different and false fact.
(b) **A post-gate refusal's dimension 1 is built exactly as a served product's
    would be**, because the same state genuinely was read.
(c) **A withheld fulfillment carries its own assessment**, and the record's
    dimension-5 debt is that assessment rather than a second measurement.
(d) **The assembler in force reaches dimension 4 for a served AND a refused
    outcome.** Asserted against the builder directly, in both directions,
    because a carriage that worked one way would be exactly the second-class
    replay the ruling forbids.
(e) **The append happens before the shell returns.** A store that refuses makes
    the resolver raise and return nothing — the same posture the served path
    has had since :mod:`ccf.replay.serve` shipped.
(f) **One question at one instant is one decision.** Two identical refusals
    converge on one content-addressed record.
(g) **The recorder answers a caller with a principal and no role** — the shape
    the governed delivery-boundary step uses for every door denial — retaining
    the resource-request identity and stamping the determination instant.

Every domain value here comes from the fixture deployment under
``tests/deployment/``, reached through the real ``load_and_boot`` that
``tests/products/test_resolver_seam.py`` already drives. Its helpers are
**imported rather than restated**: a second copy of a fixture deployment is a
second thing to keep in step, and the subject here is the record, not the boot.
"""

from __future__ import annotations

import pathlib
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN, GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.disclosure import INDISTINGUISHABLE_BELOW_FULL
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    RefusalEnvelope,
    RefusalEvidence,
    RequestIdentity,
    ResourceRequestIdentity,
    envelope_for,
)
from ccf.products.disclosure import DisclosureDecision
from ccf.products.request import ProductRequestViolation
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_ASSEMBLER,
    NO_FABRIC_READ,
    NO_PRODUCT_ADDRESS,
    NO_REQUEST_RESOLUTION,
    NO_ROLE_RESOLVED,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)

from tests.deployment.conftest import POLICY_BUNDLE_KEY, TENANT

# The two fixtures and the helpers are IMPORTED rather than restated. A second
# copy of a fixture deployment is a second thing to keep in step, and the
# subject here is the record rather than the boot — `booted_with_ceiling` in
# particular has to declare the tolerance argument on the request contract as
# well as the default on the class, and a hand-rolled copy that forgot the
# first would fail deep inside the Authority layer for the wrong reason.
from tests.composition import composition_replay_mint
from tests.products.test_resolver_seam import (  # noqa: F401
    ASKED_AT,
    MAX_TTL_SECONDS,
    REPLAY_RECORD_CLASS,
    THRESHOLD_PARAMETER,
    _ask,
    _Booted,
    _request,
    _resolver,
    _RefusingStore,
    booted,
    booted_with_ceiling,
)


def _record_at(booted: _Booted, uri: str) -> DecisionReplayRecord:
    """The record a shell's own reference resolves to.

    Resolution IS the assertion: the store refuses to hand back bytes that do
    not hash to the address asked for, so a returned record is also the claim
    that nothing was tampered with between the append and this read.
    """
    return DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=booted.store.resolve_uri(uri=uri))
    )


def _recorded_shell(record: DecisionReplayRecord) -> RefusalEnvelope:
    """The refusal dimension 5 carries, decoded back to the value it was."""
    return RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )


# --- (a) a pre-assembly refusal ---------------------------------------------


def test_a_request_conformity_refusal_is_recorded_with_nothing_read(
    booted: _Booted,
) -> None:
    """Leg (a). The whole of ``D-IMPL-253`` Q13 in one determination.

    A question the class does not answer is refused before the graph is
    touched. Until ``24.6-07`` that produced a shell and no record; now it
    produces both, and dimension 1 asserts *there is none* rather than
    describing a read that never happened.
    """
    outcome = _ask(_resolver(booted), _request(parameters={}))

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-request-violation"

    # The returned shell knows where its own record landed.
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    record = _record_at(booted, outcome.replay_reference)

    # Dimension 1: nothing was read, and it says so positively.
    assert record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ
    assert record.context_fabric_snapshot.touched_entities == ()
    assert record.context_fabric_snapshot.touched_relationships == ()
    assert record.context_fabric_snapshot.tenant_id == TENANT

    # Dimension 2: the bundle the deployment put in force.
    assert POLICY_BUNDLE_KEY in {
        binding.key for binding in record.policy_bindings.bindings
    }

    # Dimension 5: no product, and the shell as it stood BEFORE it learned its
    # own address — a record whose content address covered a reference to
    # itself could not be content-addressed at all.
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )
    recorded = _recorded_shell(record)
    assert recorded.replay_reference == NO_REPLAY_REFERENCE

    # `24.6-08`: the record holds the INTERNAL determination and the returned
    # shell holds the permitted statement, so the two are deliberately NOT the
    # same value. What must agree is the determination itself; what must differ
    # is what crossed. Both halves are asserted, because either alone passes
    # against a seam that recorded the disclosed form — which is exactly the
    # audit truth `D-IMPL-253` Q27 forbids destroying.
    assert recorded.kind == outcome.kind
    assert recorded.reason == outcome.reason
    assert recorded.key == outcome.key
    assert recorded.request == outcome.request
    assert recorded.disclosure is None, (
        "the recorded form is the internal one and nothing decided what may"
        " cross it"
    )
    assert outcome.disclosure == "minimal", (
        "no entitlement policy is registered for this fixture tenant, so the"
        " safe default applies (D-IMPL-253 Q17)"
    )
    assert recorded.detail != outcome.detail
    # Field PRESENCE is identical; only values were replaced.
    assert set(recorded.fields) == set(outcome.fields)

    # And the decision that produced the difference is recorded beside it, so
    # replay reconstructs BOTH the determination and the disclosure.
    decision = DisclosureDecision.model_validate_json(
        record.content_generation_path.disclosure_decision
    )
    assert decision.level == "minimal"
    assert decision.internal_kind == decision.external_kind == outcome.kind
    assert "detail" in decision.withheld


def test_the_store_grew_by_exactly_one_record(booted: _Booted) -> None:
    """A refusal is ONE decision, so it appends one artifact and no more.

    Counted before and after rather than asserted from the end state, and with
    the counter proven non-vacuous first: a lister that finds nothing before
    *and* nothing after would satisfy a naive delta of zero, and a lister that
    globbed the wrong pattern would report zero however many records landed.
    """
    resolver = _resolver(booted)
    before = _stored_addresses(booted)
    outcome = _ask(resolver, _request(parameters={}))
    assert isinstance(outcome, RefusalEnvelope)
    after = _stored_addresses(booted)

    added = after - before
    assert len(added) == 1, f"before={sorted(before)} after={sorted(after)}"
    assert booted.store.resolve_uri(uri=outcome.replay_reference) in added
    # The counter's positive control: a second, DIFFERENT question adds one
    # more. Without this the delta above could be produced by a lister that
    # happened to find exactly one file for an unrelated reason.
    other = _ask(resolver, _request(parameters={THRESHOLD_PARAMETER: 1}))
    # The counter counts RECORDS, served or refused: what the control needs is
    # that a second question produced an outcome at all. (Phase 24.6 close
    # panel: the earlier `isinstance(...) or other is not None` could not fail.)
    assert other is not None
    assert len(_stored_addresses(booted) - after) >= 1


#: What a stored artifact's filename looks like on the file substrate: the
#: content address, and nothing else. Measured rather than assumed —
#: `FileArtifactStore.put` writes `root / content_address` with no suffix, and
#: the name index beside it is the only dotfile. A count that globbed `*.json`
#: would find the index and miss every artifact, which is a counter that
#: reports zero however many records were appended.
_ADDRESS = re.compile(r"^[0-9a-f]{64}$")


def _stored_addresses(booted: _Booted) -> set[str]:
    """Every artifact content address the store currently holds.

    Read off the file substrate rather than through the index the writer also
    maintains, so a writer that appended nothing but registered a name cannot
    make this count look right.
    """
    root = booted.store.root
    if not root.exists():
        return set()
    return {path.name for path in root.iterdir() if _ADDRESS.match(path.name)}


# --- (b) a post-gate refusal ------------------------------------------------


def test_a_gate_refusal_records_the_state_it_actually_read(
    booted: _Booted,
) -> None:
    """Leg (b). A gate refusal HAS an execution, so dimension 1 is a real one.

    The distinction is the point: a pre-assembly refusal and a gate refusal are
    both refusals and their dimension 1 must not look the same, because one
    read the graph and the other did not. A builder that answered ``unread``
    for both would be recording a false claim about half of them.
    """
    # A product TTL above the class's registered ceiling: Gate 3 refuses.
    resolver = _resolver(booted, product_ttl_seconds=MAX_TTL_SECONDS + 1)
    outcome = _ask(resolver, _request())

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    record = _record_at(booted, outcome.replay_reference)

    assert record.context_fabric_snapshot.store_watermark != NO_FABRIC_READ
    assert record.content_generation_path.plan_id != NO_FABRIC_READ
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )
    # The permitted evidence names the search that DID happen — on the
    # INTERNAL shell. Evidence of a search is not something a refused caller is
    # owed at the safe default, so `24.6-08` withholds it on the shell and
    # keeps it in the record.
    internal = _recorded_shell(record)
    assert internal.evidence is not None
    assert internal.evidence.plan_id == record.content_generation_path.plan_id
    assert outcome.evidence is None


# --- (c) a withheld fulfillment ---------------------------------------------


def _indebted_scorer(
    *, view: GraphView, evidence: ExecutionEvidence | None = None
) -> DebtAssessment:
    """A fixture scorer whose figure exceeds the class's declared default.

    A test-side number, authored here and nowhere in ``src/`` (CINV-01). What
    it is *for* is producing a tolerance-exceeded determination through the
    real composition rather than a hand-built shell.
    """
    return DebtAssessment(
        debt=Decimal("0.9"),
        signal=DebtSignal.FAIL_CLOSED,
        factors=DebtFactors(
            freshness=Decimal("0.1"),
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        ),
        scorers=(),
    )


def test_a_withheld_fulfillment_records_the_assessment_it_was_withheld_on(
    booted_with_ceiling: _Booted,
) -> None:
    """Leg (c). One assessment, recorded once and shown once.

    The shell's permitted evidence and the record's dimension-5 debt are the
    **same** value, not two measurements that happen to agree. A composition
    that scored twice could withhold on one number and record another, which is
    the divergence a reader of the record could never detect.
    """
    resolver = _resolver(booted_with_ceiling, debt_scorer=_indebted_scorer)
    outcome = _ask(resolver, _request())

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "tolerance-exceeded"
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    record = _record_at(booted_with_ceiling, outcome.replay_reference)

    internal = _recorded_shell(record)
    assert internal.evidence is not None
    assert internal.evidence.debt is not None
    assert record.content_generation_path.debt == internal.evidence.debt
    assert record.content_generation_path.debt.debt == Decimal("0.9")
    # The evidence is INTERNAL (`24.6-08`): the safe default withholds the
    # search behind a refusal, and the record is where the one assessment
    # lives. What the shell says is the tolerance and the authority.
    assert outcome.evidence is None
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )


# --- (d) the assembler in force, both outcomes ------------------------------

_BOUNDARY = datetime(2026, 2, 1, tzinfo=UTC)
_RECORDED_AT = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _an_execution() -> ExecutionResult:
    return ExecutionResult(
        plan_id="plan-1",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-1", payload={"k": "v"}),
        view=GraphView(tenant_id="tenant-a", as_of=_BOUNDARY),
    )


def _a_product() -> ContextProductContract:
    return ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="tenant-a",
        temporal_boundary=_BOUNDARY,
        expires_at=datetime(2026, 4, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=_BOUNDARY,
        ),
        payload={"k": "v"},
    )


def _a_shell() -> RefusalEnvelope:
    return envelope_for(
        ProductRequestViolation(
            reason="missing-required-parameter",
            key=THRESHOLD_PARAMETER,
            detail="fixture",
            declared_type="d",
            presented_type="p",
            declared_keys=frozenset({THRESHOLD_PARAMETER}),
            presented_keys=frozenset(),
        ),
        request=RequestIdentity(
            product_id="ccf.test-product",
            product_version="1.0.0",
            parameters={},
            temporal_boundary=_BOUNDARY,
        ),
    )


@pytest.mark.parametrize("outcome", ["served", "refused"])
def test_the_assembler_in_force_reaches_dimension_four_on_either_outcome(
    outcome: str,
) -> None:
    """Leg (d). ``D-IMPL-253`` Q16 and ``D-IMPL-245`` amendment 1.

    Parametrized over the two outcomes and asserted for each, because a
    carriage that worked on the served path and not the refused one would be
    precisely the second-class replay Q13 forbids — and would pass a test that
    only ever built a served record.
    """
    common: dict[str, Any] = {
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (PolicyBinding(key="policy.bundle", version="v1"),),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
        "assembler_id": "fixture.assembler",
        "assembler_version": "2.1.0",
        # 24.7-04 (D-IMPL-264 D-09/D-10): a fixture-minted record states
        # that no resolution step ran in this path.
        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
    }
    if outcome == "served":
        record = build_replay_record(
            execution=_an_execution(), product=_a_product(), **common
        )
    else:
        record = build_replay_record(
            execution=None,
            product=None,
            refusal=_a_shell(),
            tenant_id="tenant-a",
            **common,
        )

    assert record.perspective_conditioning.assembler_id == "fixture.assembler"
    assert record.perspective_conditioning.assembler_version == "2.1.0"


@pytest.mark.parametrize("outcome", ["served", "refused"])
def test_no_assembler_is_asserted_rather_than_left_absent(outcome: str) -> None:
    """The control for leg (d): the sentinel is a claim, not a silence."""
    common: dict[str, Any] = {
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
    }
    if outcome == "served":
        record = build_replay_record(
            execution=_an_execution(), product=_a_product(), **common
        )
    else:
        record = build_replay_record(
            execution=None,
            product=None,
            refusal=_a_shell(),
            tenant_id="tenant-a",
            **common,
        )
    assert record.perspective_conditioning.assembler_id == NO_ASSEMBLER
    assert record.perspective_conditioning.assembler_version == NO_ASSEMBLER


def test_the_recorded_shell_never_carries_a_replay_reference() -> None:
    """A record cannot contain its own address, so the recorded shell is
    stripped — and this test exists because the strip was **unreachable**.

    Measured, not assumed. Removing the ``model_copy`` that clears
    ``replay_reference`` before minting left the whole suite green, because
    every shipped path hands the builder an envelope
    :func:`~ccf.products.refusal.envelope_for` produced, and that function
    never sets a reference. The guard was a real defense with nothing
    exercising it — a control that passes is worse than no control (plan
    ``24.6-05``'s own finding, one seam over).

    So the subject here is the case the shipped paths do not reach yet and
    ``24.6-08`` will: a shell that ALREADY carries an address being recorded
    again. The recorded form must still be the address-less one, or the
    record's own content address would cover a reference to itself and
    re-recording one determination would produce two different records of it.
    """
    already_addressed = _a_shell().model_copy(
        update={"replay_reference": "ccf-artifact://t/replay/already"}
    )
    record = build_replay_record(
        execution=None,
        product=None,
        refusal=already_addressed,
        tenant_id="tenant-a",
        perspective=Perspective(principal_id="p-1", role="analyst"),
        policy_bindings=(),
        assembly_mode="algorithmic",
        recorded_at=_RECORDED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    recorded = _recorded_shell(record)
    assert recorded.replay_reference == NO_REPLAY_REFERENCE
    assert "already" not in record.content_generation_path.assembly_refusal

    # And the two record IDENTICALLY: the address a shell happens to be
    # carrying is not a fact about the determination, so a record of the same
    # determination must not move because of it.
    without = build_replay_record(
        execution=None,
        product=None,
        refusal=_a_shell(),
        tenant_id="tenant-a",
        perspective=Perspective(principal_id="p-1", role="analyst"),
        policy_bindings=(),
        assembly_mode="algorithmic",
        recorded_at=_RECORDED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    assert canonical_bytes(record) == canonical_bytes(without)


def test_the_builder_records_exactly_one_outcome() -> None:
    """Both halves and neither are unrepresentable, not merely discouraged."""
    common: dict[str, Any] = {
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
    }
    with pytest.raises(ValueError, match="exactly one outcome"):
        build_replay_record(execution=None, product=None, **common)
    with pytest.raises(ValueError, match="exactly one outcome"):
        build_replay_record(
            execution=_an_execution(),
            product=_a_product(),
            refusal=_a_shell(),
            **common,
        )
    with pytest.raises(ValueError, match="the execution that produced it"):
        build_replay_record(execution=None, product=_a_product(), **common)
    with pytest.raises(ValueError, match="has to be stated"):
        build_replay_record(
            execution=None, product=None, refusal=_a_shell(), **common
        )
    with pytest.raises(ValueError, match="two sources for one fact"):
        build_replay_record(
            execution=_an_execution(),
            product=_a_product(),
            tenant_id="tenant-a",
            **common,
        )


# --- 24.7-04: the resolution state is explicit or the record is not built ---


def _resolution_common() -> dict[str, Any]:
    """Every builder argument EXCEPT ``resolution`` — the subject under test."""
    return {
        "execution": None,
        "product": None,
        "refusal": _a_shell(),
        "tenant_id": "tenant-a",
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
    }


def test_the_builder_refuses_a_none_resolution_by_name() -> None:
    """``D-IMPL-264`` D-10 and P-2: *"Missing resolution information is an
    internal integrity failure."* ``None`` is the omission the ruling closed,
    and the builder refuses it BY NAME rather than writing the sentinel.

    The second call has neither outcome AND no resolution, and the message
    it gets is the resolution guard's — that guard is the first in the
    block, so an integrity failure is named before any outcome is judged.
    """
    with pytest.raises(ValueError, match="an explicit resolution state"):
        build_replay_record(resolution=None, **_resolution_common())
    neither = _resolution_common()
    neither["refusal"] = None
    with pytest.raises(ValueError, match="an explicit resolution state"):
        build_replay_record(resolution=None, **neither)


def test_the_builder_refuses_an_omitted_resolution() -> None:
    """D-10: *"No implicit omission for new records."* The signature makes
    omission impossible to express — there is no default to fall back to, so
    Python itself refuses the call and names the missing keyword."""
    with pytest.raises(TypeError, match="resolution"):
        build_replay_record(**_resolution_common())
    served: dict[str, Any] = {
        "execution": _an_execution(),
        "product": _a_product(),
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
    }
    with pytest.raises(TypeError, match="resolution"):
        build_replay_record(**served)


def test_the_builder_refuses_a_pre_serialized_resolution() -> None:
    """The one-render rule (24.6-03): the marker and the resolution land as
    bytes rendered from the VALUE, never accepted as a block a caller
    serialized — a pre-serialized string could be a family of blocks."""
    block = canonical_bytes(
        ResolutionNotApplicable(reason="no-resolution-step")
    ).decode("utf-8")
    with pytest.raises(ValueError, match="never accepted pre-serialized"):
        build_replay_record(resolution=block, **_resolution_common())
    with pytest.raises(ValueError, match="never accepted pre-serialized"):
        build_replay_record(
            resolution=NO_REQUEST_RESOLUTION, **_resolution_common()
        )


@pytest.mark.parametrize(
    "reason", ["no-resolution-step", "refused-before-resolution"]
)
def test_the_marker_renders_once_from_the_value(reason: str) -> None:
    """D-09: not-applicable is a first-class fact with a reason, rendered
    through ``canonical_bytes`` exactly as a resolution is — distinguishable
    from the legacy sentinel by shape, and round-tripping as itself."""
    marker = ResolutionNotApplicable(reason=reason)
    record = build_replay_record(resolution=marker, **_resolution_common())
    rendered = record.policy_bindings.request_resolution
    assert rendered == canonical_bytes(marker).decode("utf-8")
    assert rendered != NO_REQUEST_RESOLUTION
    assert ResolutionNotApplicable.model_validate_json(rendered) == marker
    assert ResolutionNotApplicable.model_validate_json(rendered).reason == reason


def test_the_marker_states_its_reason_from_a_closed_vocabulary() -> None:
    """The reason is required and closed: an author who never stated WHY
    resolution does not apply has not stated non-applicability (P-2)."""
    with pytest.raises(ValueError):
        ResolutionNotApplicable()  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        ResolutionNotApplicable(reason="because")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ResolutionNotApplicable(reason=None)  # type: ignore[arg-type]


def test_a_fixture_minted_record_states_no_resolution_step() -> None:
    """D-09 / criterion 16 for the test-fixture class of direct minting: a
    record minted with no resolver in the path SAYS so, with the reason, and
    the claim is readable back off dimension 2 as the typed marker."""
    record = build_replay_record(
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        **_resolution_common(),
    )
    stated = ResolutionNotApplicable.model_validate_json(
        record.policy_bindings.request_resolution
    )
    assert stated.reason == "no-resolution-step"
    assert record.policy_bindings.request_resolution != NO_REQUEST_RESOLUTION


# --- (e) the append happens first -------------------------------------------


def test_a_failed_append_yields_no_shell_at_all(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """Leg (e). *A failure to record is a failure to respond.*

    ``D-IMPL-256`` refuses to make auditability contingent on the outcome, so
    the refusal path inherits the served path's posture exactly: the store's
    exception propagates and no branch reaches a returned shell.

    The attempt counter is asserted as well as the raise, because a composition
    that never reached the store would raise for some other reason and pass a
    test that only watched for an exception.
    """
    store = _RefusingStore(tmp_path / "refusing-artifacts")
    recorder = ReplayRefusalRecorder(
        authorized=composition_replay_mint(
            booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
        ),
        artifact_store=store,
        assembly_mode="algorithmic",
    )
    resolver = _resolver(booted, artifact_store=store, refusal_recorder=recorder)

    with pytest.raises(OSError):
        _ask(resolver, _request(parameters={}))

    assert store.attempts >= 1, (
        "the store must have been reached: a composition that returned the"
        " shell without attempting the append would pass a test that only"
        " watched for an exception"
    )


# --- (f) determinism --------------------------------------------------------


def test_two_identical_refusals_at_one_instant_are_one_decision(
    booted: _Booted,
) -> None:
    """Leg (f). ``D-IMPL-254``'s determinism property, on the refusal path.

    *"Same request + same governed state + same asked_at → same determination,
    authority resolution, disclosure decision, and replayable response."* The
    resolver reads no clock — ``recorded_at`` is the question's own
    ``asked_at`` — and the store is content-addressed, so two identical
    questions converge on **one** artifact rather than accumulating
    near-duplicates. That convergence is the property, and it is what lets two
    doors over one resolver report the same address.
    """
    resolver = _resolver(booted)
    first = _ask(resolver, _request(parameters={}))
    second = _ask(resolver, _request(parameters={}))

    assert isinstance(first, RefusalEnvelope)
    assert isinstance(second, RefusalEnvelope)
    assert first.replay_reference == second.replay_reference
    assert canonical_bytes(first) == canonical_bytes(second)
    assert canonical_bytes(_record_at(booted, first.replay_reference)) == (
        canonical_bytes(_record_at(booted, second.replay_reference))
    )


# --- (g) the door-level shape ------------------------------------------------


def test_the_recorder_answers_a_caller_with_a_principal_and_no_role(
    booted: _Booted,
) -> None:
    """Leg (g). The shape the governed delivery-boundary step uses.

    ``D-IMPL-256`` (1): a standing-resource denial is a governed request in a
    different request form, and *"the request identity for a standing resource
    may be a different request form, but it still needs enough identity to
    answer: what resource was requested, by whom/perspective, at what instant,
    under which policy, and why fulfillment was refused. Otherwise we would
    have just created a replay hole based on transport shape."*

    The recorder is called **directly**, with no ``ProductRequest``, no
    execution and no role — which is exactly what a door holds at the instant
    it denies entitlement, before the resolver has run. The transports never
    call this seam; the governed step does (criterion 36).
    """
    determined_at = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    resource = ResourceRequestIdentity(
        surface="fixture-surface",
        address="ccf-product://fixture.manifest-product/1.0.0",
        tenant_id=TENANT,
        determined_at=determined_at,
    )
    shell = _a_shell().model_copy(update={"resource": resource})
    recorder = ReplayRefusalRecorder(
        authorized=composition_replay_mint(
            booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
        ),
        artifact_store=booted.store,
        assembly_mode="algorithmic",
    )

    returned = recorder.record(
        shell,
        # The door's own positive claim: a principal, and NO role resolved.
        # The seam takes an already-resolved `Perspective` rather than the two
        # halves, because `15.5-RESEARCH.md` Pitfall 3 forbids a
        # `principal_id` parameter anywhere under `ccf/products`,
        # `ccf/projection` or `ccf/replay` — identity is resolved at the door.
        perspective=Perspective(
            principal_id="principal-at-the-door", role=NO_ROLE_RESOLVED
        ),
        recorded_at=determined_at,
        served_at=determined_at,
        request=None,
        execution=None,
        # 24.7-04 (D-IMPL-264 D-10 am.1): the seam requires the state too;
        # this fixture ran no resolution step and says so.
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )

    assert returned.replay_reference != NO_REPLAY_REFERENCE
    record = _record_at(booted, returned.replay_reference)

    # Dimension 1: a denial at the door read nothing.
    assert record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ
    # Dimension 4: the principal is whoever asked; the role was never resolved,
    # and the record SAYS so rather than inventing one.
    assert record.perspective_conditioning.principal_id == "principal-at-the-door"
    assert record.perspective_conditioning.role == NO_ROLE_RESOLVED
    # The determination's own instant, on the record. The returned shell is
    # DISCLOSED at this tenant's level — the safe default. Whether the resource
    # identity crosses is the Disclosure layer's per-kind decision: for
    # `subject-unavailable` — the kind every real boundary denial is minted as
    # — it is normalized below `full` (`D-IMPL-260` P-J; measured in
    # `tests/products/test_disclosure.py` and at both doors). This fixture's
    # kind is not in that table, so here it crosses, and the assertion says
    # which case this is rather than asserting presence as a rule.
    assert record.recorded_at == determined_at
    assert returned.disclosure == "minimal"
    assert "resource" not in INDISTINGUISHABLE_BELOW_FULL.get(returned.kind, ())
    assert returned.resource == resource
    # Dimension 5 retains the resource identity whole: internal truth is
    # recorded, and what may cross is the Disclosure layer's decision.
    recorded = _recorded_shell(record)
    assert recorded.resource == resource
    assert recorded.replay_reference == NO_REPLAY_REFERENCE


def test_a_recorder_with_no_bundle_pin_records_exactly_the_callers_bindings(
    booted: _Booted,
) -> None:
    """The ``policy_bundle_pin=None`` posture, measured rather than assumed.

    A door-side recorder holds no bundle key, and the honest record of that is
    *the bindings are exactly what the caller passed* — never a pin invented on
    the deployment's behalf.
    """
    recorder = ReplayRefusalRecorder(
        authorized=composition_replay_mint(
            booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
        ),
        artifact_store=booted.store,
        assembly_mode="algorithmic",
    )
    passed = (PolicyBinding(key="fixture.entitlement", version="v7"),)
    returned = recorder.record(
        _a_shell(),
        perspective=Perspective(principal_id="p-1", role=NO_ROLE_RESOLVED),
        recorded_at=ASKED_AT,
        served_at=ASKED_AT,
        policy_bindings=passed,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    record = _record_at(booted, returned.replay_reference)
    assert record.policy_bindings.bindings == passed


def test_a_recorder_holding_a_bundle_pin_prepends_it(booted: _Booted) -> None:
    """The control for the posture above: the pin is prepended, not merged."""
    pin = PolicyBinding(key=POLICY_BUNDLE_KEY, version="v-fixture")
    recorder = ReplayRefusalRecorder(
        authorized=composition_replay_mint(
            booted.control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
        ),
        artifact_store=booted.store,
        assembly_mode="algorithmic",
        policy_bundle_pin=pin,
    )
    passed = (PolicyBinding(key="fixture.entitlement", version="v7"),)
    returned = recorder.record(
        _a_shell(),
        perspective=Perspective(principal_id="p-1", role=NO_ROLE_RESOLVED),
        recorded_at=ASKED_AT,
        served_at=ASKED_AT,
        policy_bindings=passed,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    record = _record_at(booted, returned.replay_reference)
    assert record.policy_bindings.bindings == (pin, *passed)


# --- the evidence a refusal shows -------------------------------------------


def test_a_pre_assembly_refusal_shows_no_search_because_there_was_none(
    booted: _Booted,
) -> None:
    """``None`` evidence is *there was no search*, not *it was withheld*.

    The two are different facts and the Disclosure layer decides only the
    second. A shell that reported an empty :class:`RefusalEvidence` here would
    claim a search ran and found nothing.
    """
    outcome = _ask(_resolver(booted), _request(parameters={}))
    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.evidence is None

    # The distinction is load-bearing and it is asserted on the INTERNAL form,
    # because on the shell the two would be indistinguishable: a withheld
    # evidence bundle is also `None` there. So the record is where *there was
    # no search* is a claim rather than a coincidence, and the disclosure
    # decision names nothing withheld under `evidence`.
    record = _record_at(booted, outcome.replay_reference)
    internal = _recorded_shell(record)
    assert internal.evidence is None
    assert internal.disclosure is None
    decision = DisclosureDecision.model_validate_json(
        record.content_generation_path.disclosure_decision
    )
    assert "evidence" not in decision.withheld


def test_the_evidence_bundle_is_the_executions_own_facts(booted: _Booted) -> None:
    """Not re-derived: a refusal cannot describe a different search from the
    one that ran, because the same execution supplies both."""
    resolver = _resolver(booted, product_ttl_seconds=MAX_TTL_SECONDS + 1)
    outcome = _ask(resolver, _request())

    assert isinstance(outcome, RefusalEnvelope)
    record = _record_at(booted, outcome.replay_reference)
    internal = _recorded_shell(record)
    assert isinstance(internal.evidence, RefusalEvidence)
    assert internal.evidence.plan_id == record.content_generation_path.plan_id
    # The head the search ran against is NOT duplicated onto the evidence
    # (`D-IMPL-309`). It is recorded once, on dimension 1, and it is reached
    # from the shell's replay reference — which is the path this test has
    # already walked to get `record`. One authoritative place, not two that
    # can disagree.
    assert "store_snapshot_pin" not in type(internal.evidence).model_fields
    assert record.context_fabric_snapshot.store_snapshot_pin is not None
    # A search DID run here, so the disclosure decision names the evidence it
    # withheld — the positive half of the test above.
    decision = DisclosureDecision.model_validate_json(
        record.content_generation_path.disclosure_decision
    )
    assert "evidence" in decision.withheld


def test_a_recorded_refusal_round_trips_through_the_builders_own_guard() -> None:
    """The dimension-5 block admits the envelope and refuses a fabrication.

    ``_admissible_refusal_block`` widened in this row — it now admits a
    :class:`~ccf.products.refusal.RefusalEnvelope` as well as the legacy
    ``ProductRequestViolation`` block. The fabricated-block refusal it has
    always carried must still fire, or the widening turned a guard into a
    passthrough.

    The third assertion is the one this row added: ``refusal`` and
    ``assembly_refusal`` are two spellings of one dimension-5 fact, and
    accepting both would mean silently preferring one — a caller whose block
    was dropped would have no way to tell.
    """
    common: dict[str, Any] = {
        "execution": None,
        "product": None,
        "tenant_id": "tenant-a",
        "perspective": Perspective(principal_id="p-1", role="analyst"),
        "policy_bindings": (),
        "assembly_mode": "algorithmic",
        "recorded_at": _RECORDED_AT,
        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
    }
    record = build_replay_record(refusal=_a_shell(), **common)
    assert _recorded_shell(record).kind == "product-request-violation"
    # The envelope round-trips as ITSELF, not as the legacy violation form.
    assert (
        record.content_generation_path.assembly_refusal
        == canonical_bytes(
            _a_shell().model_copy(update={"replay_reference": NO_REPLAY_REFERENCE})
        ).decode("utf-8")
    )

    # The fabricated-block guard still fires on the served path, where a
    # pre-serialized block is still how the assembler seam speaks.
    with pytest.raises(ValueError, match="governed refusal"):
        build_replay_record(
            execution=_an_execution(),
            product=_a_product(),
            perspective=Perspective(principal_id="p-1", role="analyst"),
            policy_bindings=(),
            assembly_mode="algorithmic",
            recorded_at=_RECORDED_AT,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            assembly_refusal='{"looks":"like a refusal"}',
        )

    # And the two spellings cannot be supplied together.
    with pytest.raises(ValueError, match="two spellings of one"):
        build_replay_record(
            refusal=_a_shell(),
            assembly_refusal=canonical_bytes(_a_shell()).decode("utf-8"),
            **common,
        )
