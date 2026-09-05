"""The SDK's reference :class:`~ccf.products.resolver.AssemblyDebtScorerProtocol`.

Whitepaper §7.7 (Context Debt and Conditional Assessment Routing) for what
``D_c`` is; the *seam* it is measured at is SDK-defined and the ruling of record
is ``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
**Amendment A.1** (Dave, 2026-08-16). CLAUDE.md §11 requires an SDK extension to
cite this project's own decision record rather than the whitepaper, and it is
also §11 — *"Reference implementations ship alongside Protocols. For every
pluggable substrate, the SDK ships a working reference impl"* — that this module
exists to satisfy.

What was measured, and what it left
-----------------------------------
The SDK already ships the *scoring* machinery:
:class:`~ccf.halflife.debt.FreshnessScorer` (a reference ``DebtFactorScorer``
under ``D-IMPL-47``), :func:`~ccf.halflife.debt.assess_debt`,
:func:`~ccf.halflife.debt.basic_debt` and
:func:`~ccf.halflife.debt.context_debt`. What it did not ship is the thin
adapter that turns the :class:`~ccf.graph.protocols.GraphView` a question
assembled into the :class:`~ccf.halflife.assessment.DebtFactors` that machinery
consumes — so every deployment wrote one, and the Phase 17 fixture's
``resolver.py`` is the measured cost.

Amendment A.1 rules that the Protocol's own docstring *overstated* the
objection when it argued the SDK would be "choosing for every deployment": a
documented, overridable default is not a choice imposed on anyone, it is what a
reference implementation is. The docstring's real point survives and is honoured
here — **the choice is genuine, so it is made explicitly, stated at the seam,
and overridable**, never made silently. :class:`AssemblyDebtScorer`'s own
docstring carries the statement.

What this module still does not decide
--------------------------------------
Only ``F`` has an SDK measurement, and that is the tree's standing position
rather than this module's: :class:`~ccf.halflife.assessment.DebtFactors` says
so in its own words — the SDK would otherwise have to invent a required-field
vocabulary and a contradiction detector, both of which are deployment
knowledge. So ``C`` and ``S`` arrive as
:class:`~ccf.halflife.debt.DebtFactorScorerProtocol` implementations the
deployment supplies, with **no defaults**: a default factor here would be a
value nobody chose (``D-IMPL-38``) and would put a number the SDK invented
inside a delivered product's content address.

:class:`DeclaredFactor` is shipped for the deployment that has no measurement
to offer and an assumption it is willing to state. It is the honest form of
"we did not measure this": the value is the deployment's, it travels into replay
under its own :class:`~ccf.halflife.assessment.ScorerPin`, and an examiner
reading the record can tell a declared factor from a measured one without
reading any code.

Cardinality never determines Context Debt
----------------------------------------
``D-IMPL-255`` (2), Dave, verbatim: **"Cardinality never determines Context
Debt. Evidence determines Context Debt."** Until ``24.6-05`` this module had
the shortcut that ruling forbids — a view carrying no entity record returned
``F = C = S = 0``, hence ``D_c = 1``, hence ``FAIL_CLOSED``, from the *count*
of rows and from nothing else. It is gone. What replaces it is not a different
constant but a different *question*: over an empty observation set the
deployment's own completeness and consistency scorers are asked what the
evidence supports, and they are handed the execution's evidence
(:class:`ExecutionEvidence`) when they can read it
(:class:`EvidenceAwareFactorScorer`). Freshness over nothing is the
multiplicative identity, for the reason :meth:`AssemblyDebtScorer.__call__`
states.

Dave's refinement, also verbatim: *"do not let 'unattested emptiness' itself
secretly become the new Debt = 1 shortcut. It is a finding about evidence
quality."* So :func:`emptiness_of` classifies evidence and **no scorer this
module ships reads its answer**. The classification is written by the governed
resolver onto
:attr:`~ccf.products.contract.ContextProductContract.computed_empty`, where a
consumer reads it beside the Debt rather than inside it.

Algorithmic module (CINV-03). Nothing here reads a clock, calls a model, or
holds a graph handle: the decision instant arrives on the view, and the view
arrives from the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.graph.protocols import GraphView, SourceAttestation, StoreSnapshotPin
from ccf.halflife.assessment import (
    NO_SCORER_PINS,
    DebtAssessment,
    DebtFactors,
    ScorerPin,
)
from ccf.halflife.debt import DebtFactorScorerProtocol, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ccf.projection.engine import ExecutionResult

__ccf_mode__ = "algorithmic"

__all__ = [
    "DECLARED_FACTOR_SCORER_ID",
    "DECLARED_FACTOR_SCORER_VERSION",
    "AssemblyDebtScorer",
    "DeclaredFactor",
    "EvidenceAwareFactorScorer",
    "ExecutionEvidence",
    "emptiness_of",
]

#: Identity of :class:`DeclaredFactor`, pinned into replay beside the value it
#: reported (``D-IMPL-47``). Named rather than spelled at the property, so the
#: id a replay record carries and the id a test asserts come from one place.
DECLARED_FACTOR_SCORER_ID = "ccf.reference.declared-factor"

#: Version of :class:`DeclaredFactor`'s *computation*, which is "report what was
#: declared". **Not a calibration and not an artifact value** — it moves only if
#: that computation changes, exactly as
#: ``ccf.halflife.debt::FRESHNESS_SCORER_VERSION`` moves only if the decay
#: aggregation changes. The dotted digits below are a semver lane, not a number
#: this module chose about anybody's data.
DECLARED_FACTOR_SCORER_VERSION = "1.0.0"

#: The two endpoints of the ``D_c`` factor codomain, named once so the
#: empty-assembly branch reads as an assertion rather than as a bare number.
#: **Neither is a threshold, a half-life or a sensitivity**, and neither is
#: tunable: :class:`~ccf.halflife.assessment.DebtFactors` refuses anything
#: outside ``[0, 1]`` at construction, so these are the interval's own bounds.
_ZERO = Decimal(0)
_UNIT = Decimal(1)


class ExecutionEvidence(CCFContract):
    """What one execution can say about the search behind its answer.

    SDK-defined (CLAUDE.md §11); ruling of record ``D-IMPL-255`` (2), ledger
    row ``24.6-L-06``. Whitepaper §7.7 for what the Debt this feeds is.

    **A narrow, deliberately factual bundle.** It carries what the projection
    engine already observed and nothing derived: how many queries actually
    issued, which operators were invoked, which of them returned nothing, what
    the source attested about itself, and the store head the reads ran
    against. No count of rows appears here, because a row count is the
    cardinality the ruling removes from this computation, and a field for it
    would be an invitation to put it back.

    It is passed to a deployment's ``C`` and ``S`` scorers that declare
    themselves able to read it (:class:`EvidenceAwareFactorScorer`). The SDK
    ships no scorer that consumes it: what *this* evidence implies about
    completeness is deployment knowledge, exactly as ``C`` itself always was
    (``D-IMPL-38``).

    Attributes:
        queries_executed: How many graph queries the execution actually
            issued, in the engine's own count
            (:attr:`~ccf.projection.engine.ExecutionResult.executed_queries`).
            Zero is the positive *nothing was asked*, which is the difference
            between a search that found nothing and a search that never ran.
        operators_invoked: The engine-resolved operator set.
        operators_returned_empty: Those of them whose output view carried zero
            entities and zero relationships.
        source_attestation: What the source attested at the read seam, or
            ``None`` — the positive *the reader reported no attestation*.
        store_snapshot_pin: The substrate head the reads ran against, or
            :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN`.
    """

    queries_executed: int
    operators_invoked: frozenset[str]
    operators_returned_empty: frozenset[str]
    source_attestation: SourceAttestation | None
    store_snapshot_pin: StoreSnapshotPin

    @classmethod
    def of(cls, execution: "ExecutionResult") -> "ExecutionEvidence":
        """Read the evidence off one :class:`~ccf.projection.engine.ExecutionResult`.

        ``execution`` is read structurally and the projection engine is
        imported only under :data:`typing.TYPE_CHECKING`: this module is an
        algorithmic leaf and importing the engine to read five attributes off
        it would couple scoring to execution machinery for no gain.
        """
        return cls(
            queries_executed=len(execution.executed_queries),
            operators_invoked=frozenset(execution.operators_invoked),
            operators_returned_empty=frozenset(execution.empty_results),
            source_attestation=execution.source_attestation,
            store_snapshot_pin=execution.store_snapshot_pin,
        )


def emptiness_of(evidence: ExecutionEvidence) -> Literal["attested", "unattested"]:
    """Classify the QUALITY of the evidence behind an empty answer.

    SDK-defined (CLAUDE.md §11); ``D-IMPL-255`` (2). This is the whole of what
    the SDK is willing to say about *"what establishes a legitimately empty
    universe"*: that a query was actually issued, and that the source it went
    to attested something about how its answers acquire policy binding and
    lineage. It ships **no number** — no minimum query count, no coverage
    fraction, no threshold — because those are the deployment's
    (``D-IMPL-255`` (2): the declared consultation set and the source
    attestation are the deployment's to declare).

    ``"attested"`` requires all three, and each is a distinct failure:

    * at least one query executed — a plan that asked nothing learned nothing;
    * a source attestation exists — a reader that attests nothing has told us
      nothing about its own coverage;
    * neither attested mode is ``"none"`` — tier 3
      (:class:`~ccf.graph.protocols.SourceAttestation`'s unattested tier) is
      *expressible* precisely so a source can say it attests nothing, and
      taking that as attestation would read the word as its opposite.

    Otherwise ``"unattested"``, which is a statement about evidence and
    **never a Debt**. Dave, ``D-IMPL-255`` (2): *"do not let 'unattested
    emptiness' itself secretly become the new Debt = 1 shortcut. It is a
    finding about evidence quality."* Nothing in :class:`AssemblyDebtScorer`
    calls this function; the governed resolver writes its answer onto
    :attr:`~ccf.products.contract.ContextProductContract.computed_empty`.
    """
    attestation = evidence.source_attestation
    if evidence.queries_executed < 1 or attestation is None:
        return "unattested"
    if attestation.policy_binding == "none" or attestation.lineage == "none":
        return "unattested"
    return "attested"


@runtime_checkable
class EvidenceAwareFactorScorer(Protocol):
    """A ``C`` or ``S`` scorer that can also read the execution's evidence.

    SDK-defined (CLAUDE.md §11); ``D-IMPL-255`` (2). An **optional companion**
    to :class:`~ccf.halflife.debt.DebtFactorScorerProtocol` rather than a
    replacement for it: a deployment scorer that implements only ``score``
    keeps working unchanged and is called exactly as it always was, and one
    that also implements :meth:`score_with_evidence` is handed the evidence
    when the caller has any.

    Two seams rather than one widened seam, because the widened seam would
    force every existing conforming scorer to grow a parameter it does not
    read, and because ``isinstance`` against this Protocol is how
    :class:`AssemblyDebtScorer` decides which call to make — a decision that
    has to be structural, since a scorer is a deployment's object and the SDK
    has no registry of them.
    """

    def score_with_evidence(
        self,
        observations: Sequence[Observation],
        *,
        now: datetime,
        evidence: ExecutionEvidence,
    ) -> Decimal:
        """Return this scorer's factor in ``[0, 1]``, given the evidence."""
        ...


@dataclass(frozen=True)
class DeclaredFactor:
    """A debt factor the deployment **declared** rather than measured.

    SDK-defined (CLAUDE.md §11); the ruling of record is the 2026-08-16 spec's
    **Amendment A.1**, which requires the reference scorer's choices to be
    stated rather than silent. This class is how the two unmeasured factors get
    stated.

    Conforms to :class:`~ccf.halflife.debt.DebtFactorScorerProtocol`, and is the
    **one** conforming scorer whose answer does not depend on what was
    assembled: :meth:`score` reads neither ``observations`` nor ``now``. That is
    precisely why it carries an identity and a version — an assessment whose
    ``C`` was asserted and one whose ``C`` was measured would otherwise be the
    same artifact, which is the repudiation failure every pin in this fabric
    closes.

    **The SDK owes the shape and none of the value.** ``value`` has no default,
    on the ``D-IMPL-38`` discipline: a defaulted factor would put a number the
    SDK invented inside a delivered product's content address, and a consumer
    could not tell it from a measurement.

    Attributes:
        value: The factor this deployment asserts, in ``[0, 1]``. Checked here
            rather than only at :class:`~ccf.halflife.assessment.DebtFactors`,
            so a mis-declared value is refused where it was authored rather
            than three frames later.

    Raises:
        ValueError: ``value`` lies outside ``[0, 1]``.
    """

    value: Decimal

    def __post_init__(self) -> None:
        if not _ZERO <= self.value <= _UNIT:
            raise ValueError(
                "a declared debt factor must lie in [0, 1]; see"
                " `src/ccf/halflife/assessment.py::DebtFactors` for the"
                " interval the three factors share"
            )

    @property
    def scorer_id(self) -> str:
        return DECLARED_FACTOR_SCORER_ID

    @property
    def scorer_version(self) -> str:
        return DECLARED_FACTOR_SCORER_VERSION

    def score(
        self, observations: Sequence[Observation], *, now: datetime
    ) -> Decimal:
        """Return the declared value, whatever was assembled.

        Both arguments are accepted and neither is read. The signature is the
        Protocol's, so this scorer substitutes for a measuring one without any
        call site knowing which it holds; the *pin* is what tells them apart,
        and the pin travels into replay.
        """
        return self.value


@dataclass(frozen=True, kw_only=True)
class AssemblyDebtScorer:
    """The SDK's reference ``GraphView`` → ``DebtAssessment`` adapter (§7.7).

    Conforms to :class:`~ccf.products.resolver.AssemblyDebtScorerProtocol` by
    structure, and carries exactly the privileged status
    :class:`~ccf.products.resolver.GovernedResolver` carries against its own
    Protocol, which is none: the SDK invokes nothing here on its own authority,
    and a deployment substituting its own scorer loses no capability.

    **The row-selection choice, stated.** This scorer measures over **the rows
    that survived being read** — exactly the entity records carried by the view
    it is handed, and no others, because it holds no graph handle and issues no
    second read. Under
    :class:`~ccf.products.resolver.GovernedResolver` that view is the composed
    post-operator view, so any operator that dropped a row dropped it before
    debt was measured. The reason is that the seam carries one view and one
    only: recovering the rows the question *read* would need a second
    consultation at a second boundary, which the Decision Replay record does not
    describe, and would report freshness over rows the delivered payload was not
    built from. **A deployment whose product means "how fresh was the source
    data we consulted" needs the other reading and supplies its own
    :class:`~ccf.products.resolver.AssemblyDebtScorerProtocol`** — the SDK
    invokes this one never.

    **The observable consequence, so a reader can tell whether it matters to
    them.** A filtering operator moves ``F`` in whichever direction its
    survivors lean: drop the stale rows and freshness rises, drop the fresh ones
    and it falls. Where the operator plan is principal-scoped the figure
    therefore describes *this* principal's assembly rather than the tenant's.
    That is consistent with ``D-IMPL-105`` rather than a leak around it — a
    consultation a principal was refused is not part of that principal's
    ``C_required``, so there is no second figure to difference against — but it
    does mean the number is not comparable across principals, and a deployment
    that wants a tenant-wide figure is asking a different question and needs a
    different scorer.

    **What an observation is, here.** One per entity record, typed by the
    record's own ``entity_class`` and dated by its ``observed_at``. The entity
    class is the deployment's ontology vocabulary and is exactly the vocabulary
    ``λ_c`` is configured against, so nothing is invented and nothing is
    guessed: a class with no declared half-life raises
    :class:`~ccf.halflife.decay.MissingHalfLife` rather than being scored at a
    rate the SDK picked.

    **Relationships are deliberately not observations.** An edge's natural type
    is its ``relationship_type``, which would need its own ``λ_c`` row; a
    deployment that declared half-lives for its entity classes only would get a
    lookup failure instead of a number, and the SDK would have quietly widened
    what a table must declare. A deployment that wants edges in ``F`` supplies
    its own scorer.

    **The instant is read off the view, never off a clock.**
    :attr:`~ccf.graph.protocols.GraphView.as_of` is the as-of boundary the view
    was rendered at — under ``GovernedResolver`` it is the question's
    ``asked_at`` — so the figure re-computes identically at replay time through
    the same code path (whitepaper §7.10 determinism).

    **The empty assembly is scored from evidence, not from its emptiness**
    (``24.6-05``, ledger row ``24.6-L-06``; ``D-IMPL-255`` (2)). This paragraph
    previously read *"the empty assembly fails closed"* and described a branch
    that scored every factor at zero, which is ``D_c = 1``, from the row count
    alone. That branch is deleted. Dave: **"Cardinality never determines
    Context Debt. Evidence determines Context Debt."** — and its mirror,
    *"Zero source entities is not automatically high Debt."* What the empty
    case gets now is the same computation every other case gets, over the
    evidence it actually has; see :meth:`__call__` for the three factors one
    at a time.

    **The routing band stays the profile's.** This scorer never overrides
    :class:`~ccf.controlplane.artifacts.DebtProfile`'s thresholds, so a profile
    declaring a fail-closed band of one reports ``OK`` at ``D_c = 1`` — that is
    the deployment having declared it never fails closed, and correcting it here
    would be the SDK choosing a band.

    Attributes:
        table: The resolved, versioned ``λ_c`` table this deployment registered.
            An artifact, never a figure authored here.
        profile: The decision class's resolved, versioned debt profile. Supplies
            the risk sensitivity ``F`` is budgeted against and the two bands
            :func:`~ccf.halflife.debt.assess_debt` routes on. Passed already
            resolved so the caller's ``(key, version)`` pinning is explicit and
            reaches the replay record; nothing here reaches for a Control Plane
            "latest".
        completeness: The ``C`` scorer. Required with no default —
            :class:`~ccf.halflife.assessment.DebtFactors` records that the SDK
            has no reference measurement for it. :class:`DeclaredFactor` is the
            shipped way to state an assumption instead of measuring one.
        semantic_consistency: The ``S`` scorer, under the same discipline.
    """

    table: HalfLifeTable
    profile: DebtProfile
    completeness: DebtFactorScorerProtocol
    semantic_consistency: DebtFactorScorerProtocol

    def __call__(
        self, *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        """Assess ``D_c`` over the graph state ``view`` carries.

        **There is no branch on how many rows the view carries**
        (``D-IMPL-255`` (2), ``24.6-L-06``). The three factors are computed one
        at a time, each from what is available to it:

        * ``F`` — :class:`~ccf.halflife.debt.FreshnessScorer` over the
          observations, when there are any. Over an empty observation set F is
          the multiplicative **identity** ``1``: nothing was observed, so
          nothing has decayed, and ``D_c = 1 − F·C·S`` is a product whose
          identity element is one. This is an algebraic identity and not a
          domain figure (CINV-01) — the same standing this module's ``[0, 1]``
          endpoints have, and the same reasoning
          :func:`~ccf.halflife.debt.context_debt` applies to its own leading
          ``1``. It is emphatically **not** a claim that the assembly was
          fresh: the claim about an empty answer lives on the product's
          :class:`~ccf.products.contract.ComputedEmptyFinding`, and no factor
          here encodes it. Because no scorer produced that identity, **no
          freshness pin is recorded** for it — naming
          :class:`~ccf.halflife.debt.FreshnessScorer` as the producer of a
          value it never computed would be the false record the pins exist to
          prevent (:data:`~ccf.halflife.assessment.NO_SCORER_PINS`' own
          reasoning). ``C`` and ``S`` keep their pins in every case, because
          the deployment's scorers did answer.
        * ``C`` and ``S`` — the deployment's scorers, always asked. When a
          scorer satisfies :class:`EvidenceAwareFactorScorer` **and** the
          caller supplied ``evidence``, it is asked through
          ``score_with_evidence`` and receives the execution's evidence —
          queries executed, operators invoked and returned empty, source
          attestation, snapshot pin. Otherwise it is asked exactly as it
          always was. A :class:`DeclaredFactor` answers the same either way,
          which is what "declared" means.

        A deployment scorer that cannot score an empty sequence raises, and
        that raise is **the deployment's and is surfaced**, never caught here:
        the SDK substituting a number for a scorer that declined to produce
        one would be the laundering this whole ruling removes.

        ``emptiness`` never enters this computation. It is written on the
        product's finding by the governed resolver, from
        :func:`emptiness_of`, and read by **no scorer the SDK ships**
        (``D-IMPL-255`` (2): *"do not let 'unattested emptiness' itself
        secretly become the new Debt = 1 shortcut"*).

        Args:
            view: The composed post-operator view whose rows are scored.
            evidence: What the execution observed about its own search, when
                the caller has it. ``None`` — the default, and every call site
                written before ``24.6-05`` — means *no evidence was supplied*,
                under which every scorer is asked through the plain
                :class:`~ccf.halflife.debt.DebtFactorScorerProtocol` seam.

        Raises:
            ccf.halflife.decay.MissingHalfLife: an entity class in the view has
                no declared ``λ_c``. Surfaced rather than defaulted
                (INV-CH7-58): substituting a rate would report a freshness
                figure the deployment never calibrated.
            ccf.halflife.decay.TemporalOrderError: a record post-dates the
                view's own ``as_of``, which an as-of read cannot produce and a
                hand-built view can. Surfaced rather than clamped, on
                :func:`~ccf.halflife.decay.freshness`'s own reasoning.
        """
        observations = self._observations(view)
        # D-30: no cardinality branch
        freshness_scorer = FreshnessScorer(
            table=self.table, risk_sensitivity=self.profile.risk_sensitivity
        )
        # Begins at the positive `nothing declared itself the producer of
        # these factors` and grows by one entry per scorer that actually
        # answered — so a factor that no scorer produced is unpinned by
        # construction rather than by a second branch.
        pins: list[ScorerPin] = list(NO_SCORER_PINS)
        if observations:
            freshness = freshness_scorer.score(observations, now=view.as_of)
            pins.append(ScorerPin.of(freshness_scorer, factor="freshness"))
        else:
            freshness = _UNIT
        pins.append(ScorerPin.of(self.completeness, factor="completeness"))
        pins.append(
            ScorerPin.of(self.semantic_consistency, factor="semantic_consistency")
        )
        return assess_debt(
            DebtFactors(
                freshness=freshness,
                completeness=self._factor(
                    self.completeness, observations, now=view.as_of, evidence=evidence
                ),
                semantic_consistency=self._factor(
                    self.semantic_consistency,
                    observations,
                    now=view.as_of,
                    evidence=evidence,
                ),
            ),
            profile=self.profile,
            scorers=tuple(pins),
        )

    @staticmethod
    def _factor(
        scorer: DebtFactorScorerProtocol,
        observations: Sequence[Observation],
        *,
        now: datetime,
        evidence: ExecutionEvidence | None,
    ) -> Decimal:
        """Ask ``scorer`` for its factor, through the richer seam when it has one.

        The choice is structural — ``isinstance`` against
        :class:`EvidenceAwareFactorScorer` — because a scorer is a
        deployment's object and this module keeps no registry of them. Both
        conditions are required: a scorer that can read evidence is still
        asked the plain question when the caller supplied none, because a
        fabricated empty evidence bundle would be a claim nobody made.
        """
        if evidence is not None and isinstance(scorer, EvidenceAwareFactorScorer):
            return scorer.score_with_evidence(
                observations, now=now, evidence=evidence
            )
        return scorer.score(observations, now=now)

    @staticmethod
    def _observations(view: GraphView) -> tuple[Observation, ...]:
        """One dated, typed observation per entity record the view carries.

        A separate method so a test can hand it a view and read back exactly
        what the freshness computation will see, rather than inferring the
        mapping from the number that came out the other end.
        """
        return tuple(
            Observation(
                observation_type=record.claim.entity_class,
                observed_at=record.claim.observed_at,
                subject=record.claim.entity_uri,
            )
            for record in view.entities
        )
