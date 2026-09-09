"""Evidence determines Context Debt — cardinality never does (``24.6-L-06``).

Subject: :class:`ccf.products.debt_scorer.AssemblyDebtScorer` after ``24.6-05``
deleted its zero-observation branch, plus the two surfaces that branch is
replaced by — :class:`~ccf.products.debt_scorer.ExecutionEvidence` and the
optional :class:`~ccf.products.debt_scorer.EvidenceAwareFactorScorer` seam — and
:func:`~ccf.products.debt_scorer.emptiness_of`, which classifies evidence and
never produces a number.

The ruling of record is ``D-IMPL-255`` (2), Dave, verbatim:

    Cardinality never determines Context Debt. Evidence determines Context Debt.

and its refinement, which is what most of this module exists to hold:

    do not let "unattested emptiness" itself secretly become the new Debt = 1
    shortcut. It is a finding about evidence quality. The Debt scorer should
    calculate from the evidence dimensions it actually has.

Why this module is shaped the way it is
---------------------------------------
The defect this row removes was a **constant reached by a branch on a count**.
The obvious way to fail at removing it is to replace one constant with another —
zero instead of one, or ``0.9`` for "unattested" — and every such replacement
would pass a test that asserted a specific number for the empty case. So no
assertion here compares against a literal Debt. Each computes the expectation
from the fixture's own declared factors, which means a scorer that started
reporting a constant would fail *even if the constant happened to match today's
figure*, the moment a fixture declared something else.

And the branch itself is watched failing. Two sabotages put the deleted branch
back into a scratch copy of ``debt_scorer.py`` under ``tmp_path`` — one with
``D_c = 1``, one with ``D_c = 0.9``, because the criterion says *"1 or any
number"* and a control that only tried ``1`` would license the second. The
shipped predicate is fed the sabotaged subject and watched refusing it.

What each test proves
---------------------
1. **A complete, attested search that finds zero has zero Debt.** Dave, Q11:
   *"zero Debt is legitimate when complete evidence establishes that zero really
   is the answer."*
2. **An unattested empty result carries the finding AND whatever Debt the
   evidence supports** — measured against the test's own evidence-aware scorer's
   output, never against a constant.
3. **The three attestation tiers classify as the ruling says**, one assertion
   each rather than in aggregate.
4. **The evidence reaches an evidence-aware scorer and only it** — a spy records
   the call; a plain scorer is asked the plain question and receives the
   observation sequence.
5. **The two constant-Debt sabotages are RED.**
6. **An operator over an empty graph is SERVED, through a booted deployment and
   the shipped resolver**, with the finding populated and the Debt the
   deployment's own factors give — which is the end-to-end form of (1).
7. **No sabotage edited the tree.**

Every domain value — the half-life, the bands, the declared factors — is this
module's own fixture vocabulary or the ``tests/deployment`` fixture's, never an
SDK value (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.artifacts import DebtProfile, HalfLifeEntry, HalfLifeTable
from ccf.deployment import load_and_boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    GraphView,
    SourceAttestation,
)
from ccf.halflife.assessment import DebtAssessment, DebtSignal
from ccf.halflife.decay import Observation
from ccf.peering.protocol import PeerRef
from ccf.products import debt_scorer as debt_scorer_module
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import (
    AssemblyDebtScorer,
    DeclaredFactor,
    EvidenceAwareFactorScorer,
    ExecutionEvidence,
    emptiness_of,
)
from ccf.products.entitlement import product_entitlement_key
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ReplayRefusalRecorder
from ccf.projection.plan import ProjectionOutput
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    PRODUCT_CLASS_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_resolver_seam import (
    ASKED_AT,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
    MAX_TTL_SECONDS,
    PRODUCT_TTL_SECONDS,
)

# --- this module's own fixture vocabulary ------------------------------------

#: The instant every hand-built view is rendered at. A literal rather than a
#: clock read, for the reason the scorer reads ``view.as_of``.
AT = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)

#: One half-life, in seconds. A fixture calibration and never an SDK figure.
HALF_LIFE_SECONDS = 3600

#: The entity class the table calibrates. Nothing in these views carries it —
#: they are empty — but the scorer needs a table to construct, and a table that
#: calibrates nothing would make a later non-empty assertion unwritable.
CALIBRATED = "fixture.widget"

#: What the deployment DECLARES for the two factors it does not measure. The
#: expectations below are computed from this, never from a literal Debt.
DECLARED = Decimal(1)

#: What the evidence-aware completeness scorer below reports when it sees a
#: search that issued no query. A fixture judgement — the SDK ships no such
#: number and could not (``D-IMPL-255`` (2)).
UNATTESTED_COMPLETENESS = Decimal("0.5")

#: The identity a test-side scorer pins itself under.
SPY_SCORER_ID = "fixture.evidence-aware-completeness"
SPY_SCORER_VERSION = "1.0.0"

#: The three attestation tiers, by name, so a test that means "tier 3" and one
#: that means "tier 1" cannot drift into each other.
TIER_1 = SourceAttestation(
    policy_binding="assembly-stamped", lineage="graph-supplied", peer=None
)
TIER_2 = SourceAttestation(
    policy_binding="admission-verified",
    lineage="product-carried",
    peer=PeerRef(tenant_id=TENANT, peer_id="fixture-peer"),
)
TIER_3 = SourceAttestation(policy_binding="none", lineage="none", peer=None)

#: The operator key a hand-built evidence bundle names.
OPERATOR_KEY = "fixture.traversal"

#: The real module's source, read once at import. The sabotages mutate COPIES.
SCORER_PATH = pathlib.Path(debt_scorer_module.__file__)
SCORER_SOURCE = SCORER_PATH.read_bytes()

#: The anchor a sabotage replaces — the line where the deleted branch stood.
MARKER = "# D-30: no cardinality branch"


# --- the drive ---------------------------------------------------------------


def table() -> HalfLifeTable:
    return HalfLifeTable(
        semver="1.0.0",
        entries={
            CALIBRATED: HalfLifeEntry(
                half_life_seconds=HALF_LIFE_SECONDS,
                decay_driver="fixture-driver",
                supersession_event="fixture-supersession",
            )
        },
    )


def profile() -> DebtProfile:
    """A debt profile. Every figure is the fixture's; none is the SDK's."""
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal(1),
        forced_llm_threshold=Decimal("0.30"),
        fail_closed_threshold=Decimal("0.70"),
    )


def empty_view() -> GraphView:
    """A view that assembled nothing, rendered as of :data:`AT`."""
    return GraphView(tenant_id="fixture-tenant", as_of=AT, entities=())


def evidence(
    *,
    queries: int,
    attestation: SourceAttestation | None,
) -> ExecutionEvidence:
    """One execution's evidence, hand-built.

    Hand-built rather than driven, because the classification under test is a
    function of exactly these five facts and driving an engine to produce them
    would make the subject the engine.
    """
    return ExecutionEvidence(
        queries_executed=queries,
        operators_invoked=frozenset({OPERATOR_KEY}),
        operators_returned_empty=frozenset({OPERATOR_KEY}),
        source_attestation=attestation,
        store_snapshot_pin=NO_STORE_SNAPSHOT_PIN,
    )


class _EvidenceAwareCompleteness:
    """A deployment's C scorer that reads the search rather than the rows.

    The shape ``D-IMPL-255`` (2) describes: completeness derived from *"declared
    consultation universe/set; source attestation of coverage/completeness"*.
    This one is deliberately crude — it reports :data:`DECLARED` when a query
    issued and :data:`UNATTESTED_COMPLETENESS` when none did — because the point
    is that the FIGURE IS THE DEPLOYMENT'S, not that the SDK approves of it.
    """

    def __init__(self) -> None:
        self.calls: list[ExecutionEvidence] = []
        self.plain_calls: list[Sequence[Observation]] = []

    @property
    def scorer_id(self) -> str:
        return SPY_SCORER_ID

    @property
    def scorer_version(self) -> str:
        return SPY_SCORER_VERSION

    def score(
        self, observations: Sequence[Observation], *, now: datetime
    ) -> Decimal:
        self.plain_calls.append(observations)
        return DECLARED

    def score_with_evidence(
        self,
        observations: Sequence[Observation],
        *,
        now: datetime,
        evidence: ExecutionEvidence,
    ) -> Decimal:
        self.calls.append(evidence)
        return DECLARED if evidence.queries_executed >= 1 else UNATTESTED_COMPLETENESS


class _PlainCompleteness:
    """A deployment's C scorer written before the evidence seam existed."""

    def __init__(self) -> None:
        self.calls: list[Sequence[Observation]] = []

    @property
    def scorer_id(self) -> str:
        return "fixture.plain-completeness"

    @property
    def scorer_version(self) -> str:
        return "1.0.0"

    def score(
        self, observations: Sequence[Observation], *, now: datetime
    ) -> Decimal:
        self.calls.append(observations)
        return DECLARED


def scorer(
    module: types.ModuleType = debt_scorer_module,
    *,
    completeness: Any | None = None,
    semantic_consistency: Any | None = None,
) -> Any:
    """The shipped scorer — or a scratch copy's — wired against fixture artifacts."""
    return module.AssemblyDebtScorer(
        table=table(),
        profile=profile(),
        completeness=completeness
        if completeness is not None
        else DeclaredFactor(value=DECLARED),
        semantic_consistency=semantic_consistency
        if semantic_consistency is not None
        else DeclaredFactor(value=DECLARED),
    )


# --- the assertion, taking its subject as a parameter -------------------------


def assert_an_attested_complete_search_that_finds_zero_has_no_debt(
    subject: Any, *, declared: Decimal
) -> None:
    """A complete attested search that found nothing carries no Debt.

    Dave, ``D-IMPL-253`` Q11: *"zero Debt is legitimate when complete evidence
    establishes that zero really is the answer."*

    The expected Debt is **computed from** ``declared`` rather than written as a
    literal, which is what makes this fire against a scorer that replaced the
    deleted cardinality branch with a different constant: a subject reporting a
    fixed number passes only while that number coincides with the algebra, and
    the two sabotages below show it does not.

    Takes its subject as a parameter so the sabotages can hand it a scratch
    module's scorer and be watched failing — the discipline
    ``tests/products/test_reference_debt_scorer.py`` established.
    """
    assessment = subject(
        view=empty_view(),
        evidence=evidence(queries=1, attestation=TIER_1),
    )
    expected = Decimal(1) - (Decimal(1) * declared * declared)
    assert assessment.debt == expected, (
        f"a complete attested search that found zero reported D_c="
        f"{assessment.debt}, not the {expected} its own factors compose to —"
        " a number from the row count rather than from the evidence"
        " (D-IMPL-255 (2))"
    )
    assert assessment.signal is DebtSignal.OK, (
        f"the routing state was {assessment.signal}, not OK, at D_c="
        f"{assessment.debt} under a profile whose bands the fixture declares"
    )


# --- 1: the attested complete search ------------------------------------------


def test_a_complete_attested_search_that_finds_zero_has_no_debt() -> None:
    """The honest subject, first — every sabotage below expects a failure."""
    assert_an_attested_complete_search_that_finds_zero_has_no_debt(
        scorer(), declared=DECLARED
    )


def test_freshness_over_nothing_is_the_identity_and_is_not_pinned() -> None:
    """The three claims about F on an empty view, asserted one at a time.

    F is the multiplicative identity because nothing observed has decayed; it is
    **not** a claim that the assembly was fresh; and it carries no pin, because
    no scorer produced it. C and S keep theirs, because their scorers answered.
    """
    assessment = scorer()(
        view=empty_view(), evidence=evidence(queries=1, attestation=TIER_1)
    )

    assert assessment.factors.freshness == Decimal(1)
    pinned = {pin.factor for pin in assessment.scorers}
    assert "freshness" not in pinned
    assert pinned == {"completeness", "semantic_consistency"}


# --- 2: the unattested empty result -------------------------------------------


def test_an_unattested_empty_result_carries_the_finding_and_the_scorers_own_debt() -> (
    None
):
    """``unattested`` is a FINDING; the Debt is whatever the evidence supports.

    Both halves matter and neither implies the other. The classification says
    the evidence was insufficient to establish completeness. The Debt is the
    deployment's completeness scorer's own answer folded through
    ``1 − F·C·S`` — asserted **against that scorer's output**, read back off the
    spy, so a subject that started returning a constant for "unattested" fails
    here even when the constant is plausible.
    """
    completeness = _EvidenceAwareCompleteness()
    unattested = evidence(queries=0, attestation=None)

    assert emptiness_of(unattested) == "unattested"

    assessment = scorer(completeness=completeness)(
        view=empty_view(), evidence=unattested
    )

    reported = assessment.factors.completeness
    assert reported == UNATTESTED_COMPLETENESS, (
        "the fixture's own evidence-aware scorer did not reach the"
        f" computation: C={reported}"
    )
    expected = Decimal(1) - (Decimal(1) * reported * DECLARED)
    assert assessment.debt == expected, (
        f"an unattested empty result reported D_c={assessment.debt} rather"
        f" than the {expected} its own scorers' figures compose to — which is"
        " 'unattested emptiness' having become a constant (D-IMPL-255 (2))"
    )
    # And the number is genuinely the scorer's rather than a coincidence: a
    # figure of 1 would make this test agree with a constant-zero subject.
    assert reported != DECLARED, (
        "the fixture's unattested figure equals its attested one, so this test"
        " cannot tell a derived Debt from a constant — the fixture is wrong,"
        " not the subject"
    )


# --- 3: the three tiers ---------------------------------------------------------


def test_tier_one_with_a_query_is_attested() -> None:
    assert emptiness_of(evidence(queries=1, attestation=TIER_1)) == "attested"


def test_tier_two_with_a_query_is_attested() -> None:
    """A mounted admitted product attests both dimensions, so it counts."""
    assert emptiness_of(evidence(queries=1, attestation=TIER_2)) == "attested"


def test_tier_three_with_a_query_is_unattested() -> None:
    """A source that attests nothing has told us nothing about its coverage.

    Tier 3 is expressible precisely so a source can say it attests nothing;
    reading that as attestation would read the word as its opposite.
    """
    assert emptiness_of(evidence(queries=1, attestation=TIER_3)) == "unattested"


def test_an_attesting_source_with_no_query_is_unattested() -> None:
    """A plan that asked nothing learned nothing, whatever the source attests."""
    assert emptiness_of(evidence(queries=0, attestation=TIER_1)) == "unattested"


def test_a_query_against_no_attestation_is_unattested() -> None:
    assert emptiness_of(evidence(queries=1, attestation=None)) == "unattested"


# --- 4: which scorer is asked which question -----------------------------------


def test_an_evidence_aware_scorer_receives_the_evidence() -> None:
    """The spy records the call, so "it was handed the evidence" is observed."""
    completeness = _EvidenceAwareCompleteness()
    supplied = evidence(queries=1, attestation=TIER_1)

    scorer(completeness=completeness)(view=empty_view(), evidence=supplied)

    assert completeness.calls == [supplied]
    assert completeness.plain_calls == [], (
        "the evidence-aware scorer was ALSO asked the plain question — one"
        " factor, two computations"
    )
    assert isinstance(completeness, EvidenceAwareFactorScorer)


def test_a_plain_scorer_is_asked_the_plain_question() -> None:
    """A scorer written before the seam existed is called exactly as it was."""
    completeness = _PlainCompleteness()

    scorer(completeness=completeness)(
        view=empty_view(), evidence=evidence(queries=1, attestation=TIER_1)
    )

    assert len(completeness.calls) == 1
    assert tuple(completeness.calls[0]) == ()
    assert not isinstance(completeness, EvidenceAwareFactorScorer)


def test_an_evidence_aware_scorer_with_no_evidence_is_asked_the_plain_question() -> (
    None
):
    """Both conditions are required, and this is the second one.

    A fabricated empty evidence bundle would be a claim nobody made, so a
    caller that supplied none gets the plain seam even from a scorer that could
    have read one.
    """
    completeness = _EvidenceAwareCompleteness()

    scorer(completeness=completeness)(view=empty_view())

    assert completeness.calls == []
    assert len(completeness.plain_calls) == 1


# --- 5: the sabotages, on scratch copies ----------------------------------------

#: The branch ``24.6-05`` deleted, as a one-liner that fits the marker's place.
#: Written HERE rather than left in `src/` — which is the point: the branch no
#: longer exists, so a control that wants to see it fail has to supply it.
CARDINALITY_BRANCH = (
    "if not observations: return assess_debt("
    "DebtFactors(freshness={f}, completeness={c}, semantic_consistency={s})"
    ", profile=self.profile, scorers=NO_SCORER_PINS)"
)


def _scratch_scorer(
    tmp_path: pathlib.Path,
    *,
    name: str,
    freshness: str,
    completeness: str = "_ZERO",
    semantic_consistency: str = "_ZERO",
) -> types.ModuleType:
    """A copy of ``debt_scorer.py`` with the deleted branch put BACK.

    The marker is asserted to appear **exactly once** before anything is
    mutated, so a sabotage cannot silently become a no-op because the anchor
    moved or was reworded.
    """
    source = SCORER_SOURCE.decode("utf-8")
    assert source.count(MARKER) == 1, (
        "the sabotage anchor is not in `debt_scorer.py` exactly once — this"
        " control cannot fire"
    )
    mutated = source.replace(
        MARKER,
        CARDINALITY_BRANCH.format(
            f=freshness, c=completeness, s=semantic_consistency
        ),
        1,
    )
    assert mutated != source
    path = tmp_path / f"{name}.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution because `AssemblyDebtScorer` is a
    # `@dataclass` and `dataclasses` resolves its string annotations through
    # `sys.modules[cls.__module__]`. An unregistered scratch module raises
    # inside `dataclasses` rather than reaching the assertion under test, which
    # would make this control fail for a reason that is not the sabotage.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_unattested_emptiness_as_a_constant_debt_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL — the deleted branch, put back at ``D_c = 1``, fails the predicate.

    This is the defect ``24.6-L-06`` removes, reproduced and watched failing:
    every factor at zero from the row count, hence ``D_c = 1``, hence
    ``FAIL_CLOSED`` on an assembly nobody measured.
    """
    scratch = _scratch_scorer(
        tmp_path, name="debt_scorer_with_cardinality_branch", freshness="_ZERO"
    )

    subject = scorer(scratch)
    assert subject(
        view=empty_view(), evidence=evidence(queries=1, attestation=TIER_1)
    ).debt == Decimal(1), "the sabotage did not take — the copy is not sabotaged"

    with pytest.raises(AssertionError, match="rather than from the evidence"):
        assert_an_attested_complete_search_that_finds_zero_has_no_debt(
            subject, declared=DECLARED
        )
    # And the real module still passes the same predicate.
    assert_an_attested_complete_search_that_finds_zero_has_no_debt(
        scorer(), declared=DECLARED
    )


def test_any_other_constant_debt_on_empty_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL — the same branch at ``D_c = 0.9``, because the criterion says *any* number.

    A control that only tried ``1`` would license the second constant, which is
    exactly how a cardinality shortcut comes back wearing a different figure.
    """
    scratch = _scratch_scorer(
        tmp_path,
        name="debt_scorer_with_a_softer_constant",
        freshness='Decimal("0.1")',
        completeness="_UNIT",
        semantic_consistency="_UNIT",
    )

    subject = scorer(scratch)
    assert subject(
        view=empty_view(), evidence=evidence(queries=1, attestation=TIER_1)
    ).debt == Decimal("0.9"), "the sabotage did not take"

    with pytest.raises(AssertionError, match="rather than from the evidence"):
        assert_an_attested_complete_search_that_finds_zero_has_no_debt(
            subject, declared=DECLARED
        )


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The controls above mutate copies under ``tmp_path``; the module is intact."""
    assert SCORER_PATH.read_bytes() == SCORER_SOURCE
    source = SCORER_SOURCE.decode("utf-8")
    assert source.count(MARKER) == 1
    # The positive half: the branch really is absent, so the sabotage adds
    # something rather than re-adding something that never left.
    assert "if not observations:" not in source
    assert "freshness=_ZERO" not in source


# --- 6: the empty graph, through a booted deployment ----------------------------


class _EmptyProjection:
    """The deployment's Π: report how many entities the traversal assembled."""

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
        self._required = required
        self._request = request

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
        perspective: Any,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={"assembled": len(list(view.entities))},
        )


@pytest.fixture()
def booted_empty(tmp_path: pathlib.Path) -> Iterator[Any]:
    """The ``tests/deployment`` fixture booted over an EMPTY graph.

    The signal batch is deliberately **not** ingested — which is the whole
    subject: an operator that runs against a graph with nothing in it. The
    fixture in ``tests/products/test_resolver_seam.py`` seeds one entity for the
    opposite reason, and the two must not be confused.
    """
    root = tmp_path / "deployment"
    root.mkdir()
    for _key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        write_artifact(root, filename, document)
    write_artifact(root, "request-contract.yaml", REQUEST_CONTRACT_DOCUMENT)
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "request-contract.yaml",
            "key": REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(tmp_path / "evidence-derived.sqlite3")},
    )
    try:
        yield (fabric, control_plane, FileArtifactStore(root=tmp_path / "artifacts"))
    finally:
        fabric.handle.close()


def _ask_the_empty_fabric(booted: Any, *, completeness: Any | None = None) -> Any:
    """One governed serve against the empty fabric, with the shipped resolver.

    The reference :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` is
    wired rather than a fixture constant, because the subject is exactly what
    that scorer now does with an empty view. ``completeness`` varies so a
    second test can watch the evidence arrive.
    """
    fabric, control_plane, store = booted
    resolver = GovernedResolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(TRAVERSAL_KEY,),
        policy_bundle_key=POLICY_BUNDLE_KEY,
        plan_factory=lambda *, required, request: _EmptyProjection(
            required=required, request=request
        ),
        debt_scorer=AssemblyDebtScorer(
            table=table(),
            profile=profile(),
            completeness=completeness
            if completeness is not None
            else DeclaredFactor(value=DECLARED),
            semantic_consistency=DeclaredFactor(value=DECLARED),
        ),
        # `24.10-02` / `R-11`: this fixture's class declares no runtime
        # invariant, and `None` says so positively. The field carries no
        # default for every other field's reason — this class is the
        # auditable, defaultless composition.
        product_gate=None,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        capabilities=(),
        # 24.6-07: the one minting seam, over the same store this resolver
        # serves from. The four required inputs and no bundle pin — this
        # fixture holds none, and `None` means the record's bindings are
        # exactly the caller's tuple.
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=TENANT,
            assembly_mode="algorithmic",
        ),
        artifact_store=store,
        replay_record_class=REPLAY_RECORD_CLASS,
        query_pin_class=QUERY_PIN_CLASS,
        max_ttl_seconds=MAX_TTL_SECONDS,
        product_ttl_seconds=PRODUCT_TTL_SECONDS,
    )
    return resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )


def test_an_operator_over_an_empty_graph_is_served_with_its_search(
    booted_empty: Any,
) -> None:
    """C-14's empty-graph clause, end to end through the shipped resolver.

    Dave, Q12: *"An operator successfully evaluating an empty graph did compute
    something."* So this must **serve**, and it must serve with the finding — and
    with the Debt the deployment's own declared factors give, which for a
    tier-1 SQLite read that issued a query is zero.

    The reference :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` is wired
    here rather than a fixture constant, because the subject is exactly what
    that scorer now does with an empty view.
    """
    outcome = _ask_the_empty_fabric(booted_empty)

    assert isinstance(outcome, ServedProduct), (
        "an operator that ran against an empty graph was not served —"
        f" {type(outcome).__name__}"
    )
    product = outcome.product
    assert product.payload["assembled"] == 0, "the fixture graph is not empty"

    finding = product.computed_empty
    assert finding is not None, (
        "an empty answer was served with no record of the search behind it"
    )
    assert finding.operators_returned_empty
    assert finding.operators_returned_empty <= finding.operators_invoked
    assert finding.plan_id == product.plan_id
    assert finding.emptiness == "attested", (
        "the SQLite reader attests tier 1 and a query issued, so the search is"
        f" attested; got {finding.emptiness}"
    )

    assert isinstance(product.debt, DebtAssessment)
    assert product.debt.debt == Decimal(1) - (DECLARED * DECLARED), (
        "the Debt over an empty graph is not what the deployment's own declared"
        f" factors give: {product.debt}"
    )
    assert product.debt.signal is DebtSignal.OK


def test_the_ttl_fixture_figures_are_this_modules_own() -> None:
    """A guard against this module quietly reading an SDK figure (CINV-01).

    ``MAX_TTL_SECONDS`` and ``PRODUCT_TTL_SECONDS`` are imported from the
    resolver-seam module, which authors them; asserted here so an import that
    started resolving to something in ``src/`` is visible.
    """
    assert MAX_TTL_SECONDS > PRODUCT_TTL_SECONDS > 0
    assert timedelta(seconds=PRODUCT_TTL_SECONDS) < timedelta(
        seconds=MAX_TTL_SECONDS
    )


def test_the_deployments_scorer_receives_the_executions_own_evidence(
    booted_empty: Any,
) -> None:
    """The key link, measured behaviorally: the SEARCH reaches the scorer.

    A resolver that stopped passing ``evidence=ExecutionEvidence.of(execution)``
    would still serve, still carry the finding and still report the same Debt
    over this fixture — every other assertion in this module would stay green.
    That is exactly the shape of a control that cannot fire, so the property is
    asserted the only way it can be: a deployment scorer that CAN read the
    evidence is wired in, and what it received is compared against what the
    execution recorded on the product.
    """
    completeness = _EvidenceAwareCompleteness()

    outcome = _ask_the_empty_fabric(booted_empty, completeness=completeness)

    assert isinstance(outcome, ServedProduct)
    assert len(completeness.calls) == 1, (
        "the deployment's evidence-aware scorer was not handed the execution's"
        f" evidence: {completeness.calls}"
    )
    seen = completeness.calls[0]
    assert seen.queries_executed >= 1, (
        "the evidence says no query issued, but the fabric read the graph —"
        " the bundle is not this execution's"
    )
    finding = outcome.product.computed_empty
    assert finding is not None
    assert seen.operators_returned_empty == finding.operators_returned_empty, (
        "the scorer's evidence and the product's finding disagree about which"
        " operators returned empty — two records of one execution"
    )
    assert seen.operators_invoked == finding.operators_invoked
    assert completeness.plain_calls == [], (
        "the scorer was ALSO asked the plain question through the governed"
        " path — one factor, two computations"
    )
