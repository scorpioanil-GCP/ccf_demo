"""The debt shape that travels: D_c, its three factors, and the scorers in force.

Whitepaper §7.7 (D_c as the assembly-time shortfall) and
``docs/CCF_Whitepaper_1-2.md:2696`` — debt *"is a runtime signal the agent must
consume as a first-class decision input, not a log-line to be read after the
fact"*. :mod:`ccf.halflife.debt` owns the *computation*; this module owns the
*shape that reaches a consumer*.

**Why this is its own module, and not simply part of** :mod:`ccf.halflife.debt`.
D-IMPL-100 lands :class:`DebtAssessment` on
:class:`~ccf.products.contract.ContextProductContract`, and
:mod:`ccf.products.contract` cannot import :mod:`ccf.halflife.debt`: that module
reaches :mod:`ccf.controlplane.artifacts` for ``DebtProfile`` and
``HalfLifeTable`` — directly, and again transitively through
:mod:`ccf.halflife.decay` — and :mod:`ccf.controlplane.artifacts` imports
:mod:`ccf.products.contract`. A top-level import from the vessel would therefore
close a cycle at load time. The shape lives *below* both: its only dependency is
:class:`~ccf.contracts.base.CCFContract`, which is exactly what lets the vessel
carry it. :mod:`ccf.halflife.debt` re-exports every name here, so no existing
import moves and no construction site changes.

**Per factor, not a scalar** (D-IMPL-99). The three factors travel with the
answer because an examiner asking *why* a decision was escalated needs to see
which of freshness, completeness or semantic consistency collapsed, and the
multiplicative form makes that question answerable only if the inputs are
carried.

**The scorer in force is pinned beside the value** (D-IMPL-47). A factor value
is reproducible only alongside the computation that produced it: a replay that
resolved today's scorer would re-derive a number under a different measurement
and call it the same decision. The ruling committed to this pin from the start;
:class:`ScorerPin` is where it lands.

**Recency ships; salience does not** (D-IMPL-101). Recency is computable today
through :meth:`~ccf.halflife.debt.FreshnessScorer.score`. Salience has no
producer anywhere in the SDK, and none is invented here — the two shapes a
later cycle may choose between are recorded in the ruling, not anticipated in
this module.

**Evidence points beside debt, not from inside it** (D-IMPL-118).
:class:`DebtEvidencePointer` is defined here, beside the assessment it
explains, but the *carrier* is a *top-level* field on
:class:`~ccf.products.contract.ContextProductContract` — a sibling of ``debt``
rather than a member of :class:`DebtAssessment`. Nesting was the cheaper
measured option and was declined: it would have inherited replay
reconstructibility for nothing, because the shipped rehydrators already carry
``record.content_generation_path.debt`` verbatim. The ruling forwent that free
ride deliberately, buying the field its own identity on the vessel, and paid
for it with a matching member on
:class:`~ccf.replay.record.ContentGenerationPath` plus an edit to every
implementation of
:meth:`~ccf.replay.engine.ReplayEnvironment.rehydrate_product` — without both,
every replay of every product raises ``ReplayDivergence``.

**When a source last published is a different fact from how much decay the
fabric has measured** (D-IMPL-112 gap 2, D-IMPL-117).
:class:`SourceRefreshWindow` is defined here for
:class:`DebtEvidencePointer`'s reason — beside the debt figure it stands apart
from — and its carrier is a *top-level* field on
:class:`~ccf.products.contract.ContextProductContract` under the same
D-IMPL-118 branch, with the same matching member on
:class:`~ccf.replay.record.ContentGenerationPath` and the same read-back in
every rehydrator. The SDK records the instants and reads them back; it defines
no source, no cadence and no threshold, and it compares them to nothing outside
themselves — which is where recency would otherwise become salience, deferred
by D-IMPL-101. **It names no source** (D-IMPL-124): the window summarises when
the oldest and the newest of a deployment's sources last published without
publishing which systems those are, because the field's purpose is freshness
rather than source enumeration.

**What a signal obliges is bound by the deployment and named by nobody here**
(D-IMPL-112 gap 3, D-IMPL-117). :class:`SignalObligation` binds one
:class:`DebtSignal` to one *opaque* obligation reference; the calibration lives
on :class:`~ccf.controlplane.artifacts.DebtProfile`, and the reference resolved
for the signal a decision actually landed in rides
:class:`~ccf.products.contract.ContextProductContract` as a top-level field
under the same D-IMPL-118 branch as the two members above, with the same
matching member on :class:`~ccf.replay.record.ContentGenerationPath` and the
same read-back in every rehydrator. **The SDK ships no obligation vocabulary
and takes no action on one.** It validates the *key*, which is a type it owns,
and validates nothing whatever about the *value*: which operational duty a
given decision class attaches to a routing state is the context product
creator's judgement, and a closed set of duty names in this file would be the
CLAUDE.md §11 defect rather than a convenience.
``tests/invariants/test_no_obligation_vocabulary.py`` is the standing gate over
that claim.

**Decimal, never float.** These values reach the replay record and are inside
the product's content address under D-IMPL-100; floats are not bit-stable, so a
float is *refused at construction* rather than coerced. Coercion would be the
worse failure: it produces a plausible number whose provenance is a
platform-dependent binary expansion, and the address carrying it would then
depend on where the product was assembled.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Final, Literal, Protocol

from pydantic import AfterValidator, field_validator, model_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_DEBT_EVIDENCE",
    "NO_OBLIGATION_IN_FORCE",
    "NO_SCORER_PINS",
    "NO_SIGNAL_OBLIGATIONS",
    "NO_SOURCE_REFRESH_RECENCY",
    "DebtAssessment",
    "DebtEvidence",
    "DebtEvidencePointer",
    "DebtFactorName",
    "DebtFactors",
    "DebtSignal",
    "ObligationInForce",
    "ScorerPin",
    "SignalObligation",
    "SignalObligations",
    "SourceRefreshRecency",
    "SourceRefreshWindow",
]

_ZERO = Decimal(0)
_UNIT = Decimal(1)

#: The three factors of the extended form, as a closed set of names
#: (whitepaper §7.7). A ``Literal`` rather than a free string so that a pin
#: naming a factor the fabric does not compute is refused at construction: the
#: names are the SDK's own structure, never deployment vocabulary.
DebtFactorName = Literal["freshness", "completeness", "semantic_consistency"]


def _refuse_float(value: object) -> object:
    """Refuse a ``float`` before validation coerces it into a ``Decimal``.

    Shared by every debt value in this module because the reason is the same
    everywhere and stating it twice invites the two statements to drift.
    """
    if isinstance(value, float):
        raise ValueError(
            "debt values are Decimal, never float: they reach the replay "
            "record and sit inside the delivered product's content address "
            "(D-IMPL-100), and floats are not bit-stable across platforms"
        )
    return value


class DebtSignal(StrEnum):
    """The routing state an assessed D_c falls into (whitepaper §7.7 CAR).

    Members:
        OK: D_c sits below both configured bands. Nothing about debt changes
            the decision path; this is not an assertion that context is
            perfect, only that its shortfall is within the class's declared
            tolerance.
        FORCED_LLM: D_c is above the class's Forced-LLM threshold — context is
            partial or stale, and a semantic stage must be invoked *with
            explicit awareness of the debt*.
        FAIL_CLOSED: D_c is above the class's Fail-Closed threshold. The fabric
            does not know enough to support the decision. §7.7 reads missing
            counter-evidence as grounds for caution rather than reassurance, so
            this state escalates and never quietly proceeds.

    The two escalation states are deliberately distinct: Forced-LLM is *more*
    reasoning, Fail-Closed is *no* decision. Collapsing them would make an
    outage indistinguishable from a hard question.
    """

    OK = "ok"
    FORCED_LLM = "forced_llm"
    FAIL_CLOSED = "fail_closed"


class DebtFactors(CCFContract):
    """The three quality factors of the extended form (whitepaper §7.7).

    Attributes:
        freshness: F — the composition of per-observation decay curves against
            the class's ``λ_c × Risk Sensitivity`` budget
            (:class:`~ccf.halflife.debt.FreshnessScorer`).
        completeness: C — the fraction of required fields actually populated
            across the assembled sources. **Not per principal** (D-IMPL-105): a
            consultation a principal is not entitled to make is not part of
            that principal's ``C_required``, so its absence is not a shortfall.
        semantic_consistency: S — the fraction of assembled sources whose
            structured assertions agree on the entities, relationships and
            magnitudes the decision cares about.

    Each lies in ``[0, 1]``; a factor outside that interval is refused rather
    than clipped, because a clipped factor is a measurement error rendered as a
    plausible number. Decimal throughout, and a ``float`` is refused at
    construction rather than coerced — see the module docstring.

    Only F has an SDK reference scorer. C and S are supplied by the caller
    until their scorers ship (DESIGN.md §2B.4, D-IMPL-47) — the SDK would
    otherwise have to invent a required-field vocabulary and a contradiction
    detector, both of which are deployment knowledge.
    """

    freshness: Decimal
    completeness: Decimal
    semantic_consistency: Decimal

    @field_validator(
        "freshness", "completeness", "semantic_consistency", mode="before"
    )
    @classmethod
    def _factor_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("freshness", "completeness", "semantic_consistency")
    @classmethod
    def _factor_is_in_the_unit_interval(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("debt factors must lie in [0, 1]")
        return value


class _ScorerIdentity(Protocol):
    """The identity half of :class:`~ccf.halflife.debt.DebtFactorScorerProtocol`.

    Structural, and deliberately narrower than the scorer Protocol itself: a
    pin needs a scorer's *identity*, not its ability to score, and asking for
    less is what lets a deployment pin a scorer it has already run and
    discarded.
    """

    @property
    def scorer_id(self) -> str: ...

    @property
    def scorer_version(self) -> str: ...


class ScorerPin(CCFContract):
    """Which scorer produced one factor, at which version (D-IMPL-47).

    The ruling requires the scorer version *in force* to be pinned into replay,
    because a factor value is only reproducible alongside the computation that
    produced it. A replay that resolved the scorer installed *today* would
    re-derive a number under a different measurement and present it as the
    number the decision was made with — the substitution the replay plane
    exists to prevent (CLAUDE.md §7.4, D-IMPL-26).

    Attributes:
        factor: Which of the three factors this pin accounts for.
        scorer_id: Stable identity of the scorer that produced it.
        scorer_version: The version of that scorer's computation.
    """

    factor: DebtFactorName
    scorer_id: str
    scorer_version: str

    @classmethod
    def of(
        cls, scorer: _ScorerIdentity, *, factor: DebtFactorName
    ) -> "ScorerPin":
        """Pin ``scorer`` as the producer of ``factor``.

        Read off the scorer rather than passed alongside it, so the pin cannot
        name a version the scorer does not claim.
        """
        return cls(
            factor=factor,
            scorer_id=scorer.scorer_id,
            scorer_version=scorer.scorer_version,
        )


#: An assessment whose factors were supplied rather than produced by a declared
#: scorer.
#:
#: The positive assertion, in :data:`~ccf.replay.record.NO_GRAPH_QUERIES`'s
#: voice and for its reason: *no scorer declared itself the producer of these
#: factors*. Only F has an SDK reference scorer, so an unpinned assessment is
#: the ordinary posture rather than a defect — and an unpinned assessment and
#: one whose pins somebody dropped would otherwise be the same artifact, which
#: is the repudiation failure mode every sentinel in this fabric closes. The
#: empty tuple rather than a marker string because each element is a structured
#: pin and the field must stay one shape.
NO_SCORER_PINS: Final[tuple[ScorerPin, ...]] = ()


class DebtEvidencePointer(CCFContract):
    """One handle to something a debt assessment summarises (D-IMPL-118).

    SDK-defined (CLAUDE.md §11). D-IMPL-112 recorded that a bare
    ``D_c``/signal/``F`` triple is not enough to act on, and named *which
    observations contributed the decay* as the first thing missing. D-IMPL-117
    then scoped what the SDK owes about it: *"the structure and the API to
    populate and extract"*, and **none of the content**. This class is that
    structure. Which observations are worth pointing at is the context product
    creator's judgement, expressed through the product's evolutionary
    capability rather than through SDK code.

    Attributes:
        handle: The identifier of the thing pointed at. **Opaque to the SDK;
            declared by the deployment** — the discipline
            :class:`~ccf.skills.catalog.SkillRequirements` already holds. The
            SDK validates structure (type, non-blankness, uniqueness, canonical
            order) and validates nothing about meaning: it ships no entity-URI
            type, no claim-id type, no vocabulary and no default.

    **The handle carries nothing a reading principal can interpret**
    (D-IMPL-119 limbs 3 and 4). That ruling found evidence pointers
    entitlement-sensitive and the shipped assembly path *not* principal-scoped,
    and it therefore refuses a pointer naming any of ``EntityClaim``'s fields in
    an interpretable form until the scoping gap is closed. It also refuses a
    handle that is *merely encoded* rather than genuinely non-revealing — an
    obfuscated entity URI is an interpretable pointer with an extra step. Until
    a later phase adds principal scoping to the assembly path, a populated
    handle must be resolvable only through a privileged side channel inside the
    trust boundary, never by the principal reading the product.

    **Nothing here varies by principal**, which is what keeps this field's
    presence inside the product's content address compatible with D-IMPL-105:
    principal-dependent contents would give two differently-entitled principals
    different addresses for the same assembly, which is the coupling that
    ruling dissolved.
    """

    handle: str

    @field_validator("handle", mode="before")
    @classmethod
    def _handle_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("handle")
    @classmethod
    def _the_handle_is_declared(cls, value: str) -> str:
        """Refuse a blank handle, in
        :meth:`SignalObligation._the_obligation_is_declared_and_is_not_the_sentinel`'s
        first limb and for its reason.

        A pointer that points at nothing is not a stricter pointer, it is one
        wearing the costume of a pointer that points at something. Accepting it
        would make *pointed at something* and *pointed at nothing* two spellings
        of one claim, while only the second has a sentinel that says so
        (:data:`NO_DEBT_EVIDENCE`), which is the repudiation failure mode
        ``D-IMPL-38`` closes. And because this value sits inside the delivered
        product's content address (``D-IMPL-118``), the ambiguity would be
        replay-stable rather than transient: the blank would reproduce exactly,
        forever, as evidence.

        Whitespace is refused with the empty string because a handle of spaces
        is the empty string with a costume on, and the deferred alternative —
        letting a consumer discover it — is the deferral CLAUDE.md §11 refuses.

        No judgement about *meaning* is made here. Any other string is accepted
        verbatim, however unfamiliar: which handles are worth pointing at is the
        context product creator's judgement (``D-IMPL-117``), and the SDK ships
        no handle vocabulary, no format and no default.
        """
        if not value.strip():
            raise ValueError(
                "an evidence handle must be declared: a blank handle points at"
                " nothing while claiming to point at something, which is what"
                " an empty NO_DEBT_EVIDENCE carrier already asserts, and it"
                " would sit inside the product's content address as evidence"
                " (D-IMPL-38, D-IMPL-118)"
            )
        return value


def _pointers_are_unique_and_canonically_ordered(
    value: tuple[DebtEvidencePointer, ...],
) -> tuple[DebtEvidencePointer, ...]:
    """Refuse a repeated handle; store the rest in one order.

    Both halves follow
    :meth:`DebtAssessment._pins_are_one_per_factor_in_canonical_order` exactly,
    and for its reasons. Two pointers carrying one handle describe one thing
    claimed twice, which is not a stricter record but an incoherent one.
    And declaration order is not a fact about the decision, while this value
    *is* inside the delivered product's content address (D-IMPL-118), so an
    order-sensitive field would make two identical assessments hash
    differently.

    A ``tuple`` sorted here rather than a ``frozenset``: a set is order-free for
    nothing, but it would also collapse a repeated handle **silently**, and the
    repetition is exactly the incoherence worth naming out loud.
    """
    handles = [pointer.handle for pointer in value]
    if len(set(handles)) != len(handles):
        raise ValueError(
            "an evidence handle may appear at most once; two pointers "
            "carrying one handle describe a single thing claimed twice, "
            "which is an incoherent record rather than a stricter one "
            "(D-IMPL-118)"
        )
    return tuple(sorted(value, key=lambda pointer: pointer.handle))


#: What a debt assessment points at, canonically ordered and handle-unique.
#:
#: An alias rather than a field-by-field re-declaration because the carrier
#: lands in **two** places — on the vessel and on replay dimension 5 — and one
#: validated shape is what keeps those two from drifting apart.
DebtEvidence = Annotated[
    tuple[DebtEvidencePointer, ...],
    AfterValidator(_pointers_are_unique_and_canonically_ordered),
]

#: An assessment that points at nothing.
#:
#: The positive assertion, in :data:`NO_SCORER_PINS`' voice and for its reason:
#: *this assessment was computed without evidence pointers*. Never ``None``
#: meaning "unknown" (D-IMPL-38) — without a named sentinel, an assessment that
#: pointed at nothing and one whose pointers somebody dropped would be the same
#: artifact, which is the repudiation failure mode every sentinel in this
#: fabric closes. The empty tuple rather than a marker string because each
#: element is a structured pointer and the field must stay one shape.
NO_DEBT_EVIDENCE: Final[tuple[DebtEvidencePointer, ...]] = ()


class SourceRefreshWindow(CCFContract):
    """When the oldest and the newest of a deployment's sources last published.

    SDK-defined (CLAUDE.md §11), attached to the whitepaper §7.7 freshness
    hook rather than derived from it. D-IMPL-112 recorded that a reader shown a
    computed freshness figure still cannot tell when the underlying source last
    published, and D-IMPL-117 scoped what the SDK owes about it to *"a slot for
    source-refresh recency, owing no definition of a source or a cadence"*.
    This class is that slot.

    **What this fact is not**, stated so the next reader does not collapse it
    into the number beside it: it is not computed freshness
    (:class:`~ccf.halflife.debt.FreshnessScorer`'s output, which measures how
    much of a decay budget has been spent), it is not the fabric's own clock
    (:attr:`~ccf.halflife.decay.Observation.observed_at`, which records when
    the fabric *learned* something), and it is not an attestation dimension
    (:class:`~ccf.graph.protocols.SourceAttestation`, whose own scoping note
    puts temporal correctness outside what a source attests).

    **What this deliberately does not carry** (D-IMPL-124). No source
    identity, and no count. The predecessor of this class was a per-source map
    whose entries named the source each instant belonged to, and a reader
    entitled to the product could therefore learn that a given upstream system
    *exists* and *when it last published* with no check that they were entitled
    to that system's contents. Dave's ruling: *"the field's purpose is
    freshness, not source enumeration. Publish the freshness signal without
    human-interpretable source identities."* A count is source enumeration in
    aggregate — it says how many systems a deployment reads even while naming
    none — and it is not freshness, so it is outside what this slot exists for.
    Reducing a deployment's declared per-source instants to this window is the
    **deployment's** work, not the SDK's: the deployment is the only party that
    knows its own set is complete, so no reducer taking per-source instants
    ships here.

    Attributes:
        oldest_source_refresh_at: The earliest of the refresh instants the
            deployment declared. Timezone-aware; a naive instant is refused at
            construction rather than coerced, because an implicit timezone is a
            silent default (D-IMPL-38) and this value is inside the delivered
            product's content address.
        newest_source_refresh_at: The latest of those same instants, under the
            same discipline.

    **Why *oldest* and *newest* rather than *stalest* and *freshest***, which
    is the naming a later contributor will be tempted to "improve" toward.
    *Stale* and *fresh* are judgement words: a member named
    ``sources_stalest_at`` asserts that the SDK holds a notion of staleness,
    which D-IMPL-117 says it owes nothing of (*"no staleness threshold"*) and
    which D-IMPL-101 deferred as salience. *Oldest* and *newest* describe the
    ordering of two declared instants and assert nothing about whether either
    is acceptable.

    **Two instants rather than one** because a single instant cannot express
    the span. With sources on different cadences a lone "newest" hides the
    oldest and a lone "oldest" hides the newest, and D-IMPL-112 gap 2's whole
    complaint was that a reader could not tell how old the underlying filings
    were.

    **Recorded, never judged** (D-IMPL-101). No function in the SDK compares a
    window instant to ``now``, to a cadence or to a threshold, and no such
    comparison may be added: deciding that one refresh matters more than
    another is salience, which that ruling deferred and for which no mechanism
    lands in this phase. Whether a January refresh is recent enough for a
    particular decision is the context product creator's judgement, expressed
    through the product's evolutionary capability rather than through SDK code.
    The one comparison this class does make is ``oldest`` against ``newest``,
    which draws no conclusion — it checks that a single declared fact is
    internally coherent.
    """

    oldest_source_refresh_at: datetime
    newest_source_refresh_at: datetime

    @field_validator("oldest_source_refresh_at", "newest_source_refresh_at")
    @classmethod
    def _the_instant_names_its_zone(cls, value: datetime) -> datetime:
        """Refuse a naive instant rather than reading a zone into it.

        :attr:`~ccf.halflife.decay.Observation.observed_at`'s discipline,
        restated at construction because this value is hashed: a coerced zone
        would make the same refresh fact produce different bytes depending on
        where the product happened to be assembled.
        """
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "a source refresh instant must name its zone; a naive datetime "
                "carries an implicit timezone, which is a silent default "
                "(D-IMPL-38), and this value is inside the delivered product's "
                "content address"
            )
        return value

    @model_validator(mode="after")
    def _the_window_does_not_end_before_it_begins(self) -> SourceRefreshWindow:
        """Refuse a window whose oldest end is after its newest end.

        The duplicate-reference refusal this class replaces, in the same voice
        and for its reason: a window ending before it begins describes two
        facts claiming to be one, which is an incoherent record rather than a
        stricter one. Equality is legal — one source, or several that published
        together, is a window of zero span.

        **This is not the forbidden comparison** (D-IMPL-101). The forbidden
        comparisons are against ``now``, against a threshold and against a
        cadence, each of which draws a conclusion about whether a value is
        acceptable. This one draws none; it checks one declared fact against
        itself.
        """
        if self.oldest_source_refresh_at > self.newest_source_refresh_at:
            raise ValueError(
                "a source refresh window may not end before it begins; an "
                "oldest instant after its newest describes two facts claiming "
                "to be one, which is an incoherent record rather than a "
                "stricter one (D-IMPL-117, D-IMPL-124)"
            )
        return self


#: The freshness window a product publishes, or nothing.
#:
#: An alias rather than a field-by-field re-declaration for
#: :data:`DebtEvidence`'s reason: the slot lands in **two** places — on the
#: vessel and on replay dimension 5 — and one named shape is what keeps those
#: two from drifting apart. It keeps the name it had when it carried a
#: per-source map (D-IMPL-124 reshapes what it carries, not where it lands).
SourceRefreshRecency = SourceRefreshWindow | None

#: A product that records no source-refresh recency.
#:
#: The positive assertion, in :data:`NO_SCORER_PINS`' voice and for its reason:
#: *this product records nothing about when its sources last refreshed*. Never
#: a bare ``None`` meaning "unknown" (D-IMPL-38) — without a named sentinel, a
#: deployment that knows nothing about its sources' publication schedule and one
#: whose recency somebody dropped in transit would be the same artifact, which
#: is the repudiation failure mode every sentinel in this fabric closes. What
#: the name buys is that every construction site and every default **spells the
#: claim** rather than leaving a bare ``None`` for a reader to interpret.
#:
#: **Its value moved from** ``()`` **to** ``None`` **under D-IMPL-124**, and the
#: reason is recorded here so a reviewer does not read it as drift: ``()`` is
#: the empty case of a *collection*, and a window is not a collection. There is
#: no empty window that does not require inventing an instant, and an invented
#: instant is the silent default D-IMPL-38 forbids. The same-vessel precedent is
#: exact — :attr:`~ccf.products.contract.ContextProductContract.debt` and
#: ``.request`` are both optional *structures* whose ``None`` is documented as a
#: positive assertion in the same voice.
NO_SOURCE_REFRESH_RECENCY: Final[SourceRefreshWindow | None] = None


#: The obligation a decision was under when no binding covered its signal.
#:
#: The positive assertion, in :data:`~ccf.products.contract.NO_PAYLOAD_SCHEMA`'s
#: voice and for :data:`NO_SCORER_PINS`' reason: *no obligation was bound to the
#: state this decision landed in*. Never ``None`` meaning "unknown"
#: (D-IMPL-38) — without a named sentinel, a decision whose deployment bound
#: nothing and one whose obligation somebody dropped in transit would be the
#: same artifact, which is the repudiation failure mode every sentinel in this
#: fabric closes. A marker string rather than an empty tuple because the field
#: holds one reference and must stay one shape; a marker rather than ``""``
#: because an empty string is what a half-finished edit leaves behind, and the
#: two claims are different. It is **not** an obligation and no deployment may
#: declare it as one — :class:`SignalObligation` refuses the spelling.
#:
#: **SDK-namespaced on purpose.** ``ccf.``-prefixed so the marker reads as SDK
#: structure rather than as a word from somebody's domain — the discipline
#: ``tests/halflife/test_debt_delivery.py`` already enforces over every
#: module-level string in this package — and so a deployment cannot collide with
#: it by accident while reaching for an ordinary phrase.
NO_OBLIGATION_IN_FORCE: Final[str] = "ccf.no-obligation-in-force"


def _the_obligation_carried_is_declared_or_is_the_sentinel(value: str) -> str:
    """Admit the sentinel or a declared reference — and nothing between them.

    The **carrying** side's rule, and deliberately not
    :meth:`SignalObligation._the_obligation_is_declared_and_is_not_the_sentinel`.
    A *binding* refuses the sentinel spelling, because a declared obligation
    wearing it would impersonate the absence. A *carrier* requires it, because
    it is the carrier's own default and the positive assertion an unobliged
    decision is spelled with. One string, two positions, two rules — and both
    rules exist to keep the same two claims apart.

    What is refused here is the third state neither rule has a name for: a blank
    (``D-IMPL-38``). A carrier holding ``""`` asserts neither *no obligation was
    bound* nor *this obligation was bound*, and because it sits inside the
    delivered product's content address and inside dimension 5 of the replay
    record, the ambiguity is **replay-stable** — it reproduces exactly, forever,
    and no reader can tell it from either legitimate claim. Refusing it at the
    boundary rather than downstream is CLAUDE.md §11.

    Nothing about *meaning* is judged. Any other string is admitted verbatim,
    however unfamiliar: the SDK ships no obligation vocabulary (``D-IMPL-117``).
    """
    if not value.strip():
        raise ValueError(
            "the obligation in force must be either a declared reference or"
            f" exactly {NO_OBLIGATION_IN_FORCE!r}: a blank is a third state"
            " that asserts neither, and it would reproduce inside the"
            " product's content address and dimension 5 of the replay record"
            " as if it did (D-IMPL-38, D-IMPL-118)"
        )
    return value


#: What a decision was obliged to do, as it travels on a carrier.
#:
#: An alias rather than a field-by-field re-declaration, in :data:`DebtEvidence`'
#: shape and for its reason: the value lands in **two** places — on
#: :class:`~ccf.products.contract.ContextProductContract` and on replay
#: dimension 5 — and one validated shape is what keeps those two from drifting
#: apart. Before this alias existed the vessel field was a bare ``str`` with no
#: validator at all, which Phase 15.6's close-time cross-AI panel found by
#: inspection.
ObligationInForce = Annotated[
    str, AfterValidator(_the_obligation_carried_is_declared_or_is_the_sentinel)
]


class SignalObligation(CCFContract):
    """What one routing state obliges, as the deployment declares it.

    SDK-defined (CLAUDE.md §11), attached to the whitepaper §7.7 CAR hook rather
    than derived from it. D-IMPL-112 recorded that a reader shown a routing
    state still cannot tell what that state *requires of them*, and D-IMPL-117
    scoped what the SDK owes about it to *"a signal-to-obligation binding that
    survives replay, and owes no obligation vocabulary"*. This class is that
    binding's element.

    **The asymmetry that makes this a gap, rather than a nicety.**
    :attr:`DebtSignal.FORCED_LLM` is produced at one site and consumed at none,
    while the other two states each have exactly one consumer in the shipped
    tree. The SDK already acts on two thirds of its own enum, so it is entitled
    to ship the *mechanism* by which a deployment says what the third means —
    and entitled to nothing beyond that.

    Attributes:
        signal: Which routing state this binding answers to. The **one half the
            SDK owns**, so it is the one half the SDK validates: a binding
            naming a state the fabric never produces is refused at construction
            with the offending key in the message.
        obligation_ref: What that state obliges. **Opaque to the SDK; declared
            by the deployment** — the discipline
            :class:`~ccf.skills.catalog.SkillRequirements` already holds. The
            SDK ships no obligation type, no obligation vocabulary and no
            default; it never parses the value, never compares it against a
            permitted set, and never branches on it.

    **Carried, never acted on.** Binding an obligation does not make the fabric
    perform it. Nothing in the SDK reads this reference and does something: a
    module that branched on it would have decided what an obligation *means*,
    which is the judgement D-IMPL-117 assigns to the context product creator and
    which ``tests/invariants/test_no_obligation_vocabulary.py`` exists to keep
    out of this file.
    """

    signal: DebtSignal
    obligation_ref: str

    @field_validator("signal", mode="before")
    @classmethod
    def _the_key_names_a_routing_state(cls, value: object) -> object:
        """Refuse an unknown key by name rather than by enum-membership error.

        A profile author meets this validator through a YAML document, where
        the natural failure — a near-miss spelling of a state — is best
        answered with the offending key and the set it had to come from. The
        SDK is entitled to this check precisely because the key type is its
        own; the value beside it gets no such treatment.
        """
        if isinstance(value, DebtSignal):
            return value
        known = tuple(member.value for member in DebtSignal)
        if not isinstance(value, str) or value not in known:
            raise ValueError(
                f"{value!r} is not a debt signal: an obligation binds to one of"
                f" {known}, the routing states the fabric actually produces"
                " (whitepaper §7.7 CAR). The SDK validates the key because the"
                " key is its own type, and validates nothing about what the"
                " obligation means (D-IMPL-117)"
            )
        return value

    @field_validator("obligation_ref", mode="before")
    @classmethod
    def _obligation_ref_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("obligation_ref")
    @classmethod
    def _the_obligation_is_declared_and_is_not_the_sentinel(cls, value: str) -> str:
        """Refuse a blank reference and refuse the sentinel's own spelling.

        Both refusals protect one distinction. A blank reference is what a
        half-finished profile edit leaves behind, and accepting it would make
        *declared, obliging nothing* and *not declared* two spellings of one
        claim — while only the second has a sentinel that says so. The sentinel
        spelling is refused for the same reason from the other direction: a
        binding that impersonated it would collapse the distinction D-IMPL-38
        requires it to hold open.

        Neither refusal is a judgement about *meaning*. Any other string is
        accepted verbatim, however unfamiliar.
        """
        if not value.strip():
            raise ValueError(
                "an obligation reference must be declared: a blank reference"
                " makes a binding that obliges nothing indistinguishable from"
                f" no binding at all, which is what {NO_OBLIGATION_IN_FORCE!r}"
                " already asserts (D-IMPL-38)"
            )
        if value == NO_OBLIGATION_IN_FORCE:
            raise ValueError(
                f"{NO_OBLIGATION_IN_FORCE!r} is reserved: it is the positive"
                " assertion that no obligation was bound, and a declared"
                " obligation wearing that spelling would collapse the"
                " distinction the sentinel exists to hold open (D-IMPL-38)"
            )
        return value


def _obligations_are_one_per_signal_in_canonical_order(
    value: tuple[SignalObligation, ...],
) -> tuple[SignalObligation, ...]:
    """Refuse a second obligation for a signal; store the rest in one order.

    Both halves follow
    :meth:`DebtAssessment._pins_are_one_per_factor_in_canonical_order` exactly,
    and for its reasons. Two obligations for one state describe two duties
    claiming to be the one thing that state requires, which is not a stricter
    calibration but an incoherent one. And declaration order is not a fact about
    the calibration, while the profile carrying it *is* content-addressed and
    version-pinned per agent, so an order-sensitive collection would make two
    identical calibrations resolve as two artifacts.

    A ``tuple`` sorted here rather than a mapping: a YAML mapping keeps the
    **last** of two duplicate keys silently, and a signal bound twice is exactly
    the contradiction a profile author needs told about.
    """
    signals = [binding.signal for binding in value]
    if len(set(signals)) != len(signals):
        raise ValueError(
            "a debt signal may carry at most one obligation; two bindings for "
            "one signal describe two duties claiming to be the single thing "
            "that state requires, which is an incoherent calibration rather "
            "than a stricter one (D-IMPL-117)"
        )
    return tuple(sorted(value, key=lambda binding: binding.signal.value))


#: What each routing state obliges, canonically ordered and signal-unique.
#:
#: An alias rather than a field-by-field re-declaration for
#: :data:`DebtEvidence`'s reason: one validated shape is what keeps the
#: declaration and everything downstream of it from drifting apart.
SignalObligations = Annotated[
    tuple[SignalObligation, ...],
    AfterValidator(_obligations_are_one_per_signal_in_canonical_order),
]

#: A calibration that binds no obligation to any signal.
#:
#: The positive assertion, in :data:`NO_SCORER_PINS`' voice and for its reason:
#: *this profile binds no obligation to any routing state*. Never ``None``
#: meaning "unknown" (D-IMPL-38) — without a named sentinel, a deployment that
#: deliberately declared no obligations and one whose bindings somebody dropped
#: would be the same artifact. It is also exactly what every profile written
#: before this field existed was already asserting, which is why the field
#: defaults rather than demands. The empty tuple rather than a marker string
#: because each element is a structured binding and the field must stay one
#: shape.
NO_SIGNAL_OBLIGATIONS: Final[tuple[SignalObligation, ...]] = ()


class DebtAssessment(CCFContract):
    """One D_c computation, the routing state it lands in, and what produced it.

    Carries the factors it was computed from, not just the scalar: an examiner
    asking *why* a decision was escalated needs to see which of the three
    dimensions collapsed, and the multiplicative form makes that question
    answerable only if the inputs travel with the answer (D-IMPL-99).

    **This type is delivered, not merely logged** (D-IMPL-100). It is carried on
    :class:`~ccf.products.contract.ContextProductContract`, so it is inside the
    product's content address and reaches every consumer the vessel reaches; and
    it is carried on the Decision Replay record's dimension 5, so a replay
    rebuilds the same bytes rather than diverging on a value it cannot
    reconstruct.

    Attributes:
        debt: D_c in ``[0, 1]``.
        signal: The CAR state (:class:`DebtSignal`).
        factors: The F/C/S inputs.
        scorers: The scorers in force, one per accounted factor, in a canonical
            order (D-IMPL-47). Defaults to :data:`NO_SCORER_PINS`.
    """

    debt: Decimal
    signal: DebtSignal
    factors: DebtFactors
    scorers: tuple[ScorerPin, ...] = NO_SCORER_PINS

    @field_validator("debt", mode="before")
    @classmethod
    def _debt_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("scorers")
    @classmethod
    def _pins_are_one_per_factor_in_canonical_order(
        cls, value: tuple[ScorerPin, ...]
    ) -> tuple[ScorerPin, ...]:
        """Refuse a second pin for a factor; store the rest in one order.

        Two pins for one factor describe two computations claiming to have
        produced one value, which is not a stricter record but an incoherent
        one. The ordering follows ``graph_secret_refs``' reasoning exactly:
        declaration order is not a fact about the decision, and this value is
        inside the delivered product's content address, so an order-sensitive
        field would make two identical assessments hash differently.
        """
        factors = [pin.factor for pin in value]
        if len(set(factors)) != len(factors):
            raise ValueError(
                "a factor may carry at most one scorer pin; two pins for one "
                "factor describe two computations claiming to have produced "
                "the same value (D-IMPL-47)"
            )
        return tuple(sorted(value, key=lambda pin: pin.factor))

    @field_validator("debt")
    @classmethod
    def _debt_is_in_the_unit_interval(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("D_c must lie in [0, 1]")
        return value
