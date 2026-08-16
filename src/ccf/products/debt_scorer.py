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

Algorithmic module (CINV-03). Nothing here reads a clock, calls a model, or
holds a graph handle: the decision instant arrives on the view, and the view
arrives from the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import (
    NO_SCORER_PINS,
    DebtAssessment,
    DebtFactors,
    ScorerPin,
)
from ccf.halflife.debt import DebtFactorScorerProtocol, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation

__ccf_mode__ = "algorithmic"

__all__ = [
    "DECLARED_FACTOR_SCORER_ID",
    "DECLARED_FACTOR_SCORER_VERSION",
    "AssemblyDebtScorer",
    "DeclaredFactor",
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

    **The empty assembly fails closed.** A view carrying no entity record scores
    every factor at zero, which is ``D_c = 1``, and carries **no scorer pin**:
    nothing measured anything, so naming a scorer as the producer of those
    zeroes would be a false record.
    :meth:`~ccf.halflife.debt.FreshnessScorer.score` refuses an empty sequence
    by design — *"the fabric retrieved nothing" is a coverage statement* — so
    there is no "call it anyway" branch to take, and reporting a confident
    number about a graph that said nothing is the precise failure the
    fail-closed posture exists to prevent. ``S`` is zero rather than one for the
    same reason: over zero sources the fraction is undefined, and an undefined
    fraction reported as perfect agreement is that laundering again. It does not
    move ``D_c``, which the multiplicative form has already driven to one
    (INV-CH7-62).

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

    def __call__(self, *, view: GraphView) -> DebtAssessment:
        """Assess ``D_c`` over the graph state ``view`` carries.

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
        if not observations:
            return assess_debt(
                DebtFactors(
                    freshness=_ZERO,
                    completeness=_ZERO,
                    semantic_consistency=_ZERO,
                ),
                profile=self.profile,
                scorers=NO_SCORER_PINS,
            )
        freshness_scorer = FreshnessScorer(
            table=self.table, risk_sensitivity=self.profile.risk_sensitivity
        )
        scorers: tuple[DebtFactorScorerProtocol, ...] = (
            freshness_scorer,
            self.completeness,
            self.semantic_consistency,
        )
        return assess_debt(
            DebtFactors(
                freshness=freshness_scorer.score(observations, now=view.as_of),
                completeness=self.completeness.score(
                    observations, now=view.as_of
                ),
                semantic_consistency=self.semantic_consistency.score(
                    observations, now=view.as_of
                ),
            ),
            profile=self.profile,
            scorers=(
                ScorerPin.of(scorers[0], factor="freshness"),
                ScorerPin.of(scorers[1], factor="completeness"),
                ScorerPin.of(scorers[2], factor="semantic_consistency"),
            ),
        )

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
