"""Typed Control Plane artifact classes (whitepaper §7.8; DESIGN.md §7).

§7.8 makes the Control Plane the place where the fabric's permitted behaviour
is declared; the artifacts in this module are how it says so. Each is a
:class:`~ccf.contracts.base.CCFContract` — frozen, closed-world, canonically
serializable — which buys three properties the registry alone cannot:

**Registering the wrong thing is a detectable error.** A bare mapping stored
under a λ_c key looks exactly like a correct one until a decay computation
reads it. A typed class turns that into a validation failure at registration,
before anything can be decided against it.

**Every artifact carries its own semver lane.** ``semver`` is a declared field
with no default, so an artifact whose author never stated its lane cannot be
registered. Lanes are per artifact class and never compared across classes
(the same discipline as per-product-class schema lanes, INV-CH7-49).

**Values stay out of code.** These classes declare *shape* only. There is no
half-life in the λ_c table class, no threshold in the debt profile class, and
no key name anywhere: the whitepaper's own λ_c table is illustrative
(§7.7), calibration is the deployment's (INV-CH7-58/59), and a number the SDK
chose is a number no examiner can trace to a decision anyone made
(CLAUDE.md §11, CINV-01; D-IMPL-38).

Artifact classes whose *schema* belongs to a deployment rather than to the SDK
— policy bundles, ontology declarations, **deployment-authored** operator
parameter sets — use :class:`DeclaredArtifact`, which fixes the envelope (class
identity, lane, canonical serializability) while leaving the declaration itself
open. The SDK does not get to invent a policy-bundle schema on a user's behalf.

The rule is *the SDK owns the schema of what it ships and never invents one for
what it does not*, which is narrower than "operator parameter sets belong to the
deployment". The four operator categories the SDK ships have typed classes
(:class:`OperatorParametersArtifact` and its subclasses) precisely because their
parameter contracts are already ``/src`` code — :mod:`ccf.operators.params`,
whose own docstring calls them Control Plane values a deployment declares,
versions and replays against. A category the SDK does not ship is a
deployment-authored schema and takes the open envelope.

Where the primitives live
-------------------------

:class:`ArtifactClass`, :class:`VersionedArtifact` and :func:`validate_semver`
are defined in :mod:`ccf.controlplane.artifact_base` and re-exported here, so
every import path that predates that module still resolves. They sit there
rather than here because this module names
:class:`~ccf.assembly.worker.EntityResolutionSpec` to declare
:data:`RESOLUTION_SPEC`, and ``ccf.assembly.worker`` reaches
``ccf.controlplane.registry``, which needs ``ArtifactClass`` — leaving it here
would close ``artifacts -> worker -> registry -> artifacts`` at import time. See
that module's docstring for the constraint that keeps the cycle broken.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Final, Literal, get_args

import yaml
from pydantic import Field, field_validator, model_validator

from ccf.assembly.worker import EntityResolutionSpec
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.graph.protocols import LineageMode, PolicyBindingMode
from ccf.controlplane.artifact_base import (
    ArtifactClass,
    VersionedArtifact,
    validate_semver,
)
from ccf.halflife.assessment import (
    NO_OBLIGATION_IN_FORCE,
    NO_SIGNAL_OBLIGATIONS,
    DebtSignal,
    SignalObligations,
)
from ccf.operators.params import (
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalDescendantsParameters,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ChildRequirement,
    NO_PAYLOAD_SCHEMA,
    NO_PRODUCT_GATE,
    NO_SERVE_OBLIGATIONS,
    NO_VALIDITY_FLOORS,
    NOT_ADDRESSABLE,
    NOT_DISCOVERABLE,
    UNMEASURED_FRESHNESS_SLA,
    AssemblyMode,
    ConstituentValidityFloors,
    DeclaredProductGate,
    FreshnessSLA,
    ProductAddress,
    ProductDiscovery,
    ServeObligations,
    TTLAnchor,
)
from ccf.products.request import NO_REQUEST_CONTRACT
from ccf.projection.plan import Perspective
from ccf.signal.envelope import SignalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = [
    "CONSTRAINT_OPERATORS",
    "DEBT_PROFILE",
    "DEPLOYMENT_CONFIG",
    "DEPLOYMENT_MANIFEST",
    "HALF_LIFE_TABLE",
    "OPERATOR_PARAMETERS_POLICY",
    "OPERATOR_PARAMETERS_SIMILARITY",
    "OPERATOR_PARAMETERS_TEMPORAL",
    "OPERATOR_PARAMETERS_TRAVERSAL",
    "OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS",
    "PERSPECTIVE",
    "POLICY_CONSTRAINT",
    "PRODUCT_CLASS",
    "PROJECTION_REQUIREMENTS",
    "MCP_PRODUCER",
    "EGRESS_DOOR",
    "EgressDoorBinding",
    "TTL_BINDING",
    "TtlBinding",
    "McpProducerRegistration",
    "ProducerOfferDeclaration",
    "REPLAY_BINDING",
    "RESOLUTION_SPEC",
    "SIGNAL_BATCH",
    "ArtifactClass",
    "ArtifactLoadError",
    "ArtifactRole",
    "ConstraintApplicability",
    "ConstraintOperator",
    "DebtProfile",
    "DecayMode",
    "DeclaredArtifact",
    "DeploymentConfig",
    "DeploymentManifest",
    "HalfLifeEntry",
    "HalfLifeTable",
    "ManifestEntry",
    "OperatorParametersArtifact",
    "PerspectiveArtifact",
    "PolicyConstraint",
    "RequestBoundParameter",
    "PolicyFilterParametersArtifact",
    "ProductClassDeclaration",
    "SeamRefusalBinding",
    "ProjectionRequirements",
    "RegistrationMode",
    "ReplayBinding",
    "SecretReference",
    "SignalBatch",
    "SimilaritySelectParametersArtifact",
    "TemporalAsOfParametersArtifact",
    "TraversalDescendantsParametersArtifact",
    "TraversalNeighborhoodParametersArtifact",
    "VersionedArtifact",
    "declared_artifact_class",
    "load_artifact",
    "parse_artifact",
    "validate_semver",
]

#: Retained name for the base that moved to
#: :mod:`ccf.controlplane.artifact_base` and became public there. Every existing
#: subclass and every reference in the plan record keeps resolving through it.
_VersionedArtifact = VersionedArtifact

_UNIT = Decimal(1)
_ZERO = Decimal(0)


class ArtifactLoadError(ValueError):
    """A serialized artifact cannot be admitted as written.

    Raised — never repaired — because the two failure modes it covers are both
    silent-corruption risks: a YAML float (not bit-stable across platforms, and
    refused outright by the canonical serializer) and a document that does not
    satisfy its declared class contract.
    """


class DeclaredArtifact(VersionedArtifact):
    """An artifact whose *schema* is the deployment's, not the SDK's.

    Policy bundles, ontology declarations, **deployment-authored** operator
    parameter sets: the whitepaper fixes that these are versioned Control Plane
    artifacts, not what fields they hold. This envelope supplies the parts that
    are mechanism — class identity, semver lane, canonical serializability — and
    leaves ``declaration`` open. Anything inside it must still be canonically
    serializable, so a float in a declaration fails at registration.

    The qualifier on operator parameter sets is load-bearing. The four categories
    the SDK ships — traversal, temporal, policy, similarity — have typed classes
    (:class:`OperatorParametersArtifact` and its subclasses), because the SDK
    already owns those parameter contracts in :mod:`ccf.operators.params` and an
    open envelope over a schema the SDK wrote would be refusing to validate what
    it can. The envelope's reason is unchanged for everything else: the SDK does
    not get to invent a policy-bundle schema on a user's behalf.

    Attributes:
        class_id: Which declared class this is an instance of.
        declaration: The deployment's own content.
    """

    class_id: str
    declaration: Mapping[str, Any]


def declared_artifact_class(class_id: str) -> ArtifactClass:
    """Return an :class:`ArtifactClass` for a user-declared artifact class."""
    return ArtifactClass(class_id=class_id, contract=DeclaredArtifact)


#: Which of the two decay paths a λ_c row takes in
#: :func:`ccf.halflife.decay.freshness` (ledger row ``24.5-L-22``; whitepaper
#: §7.7.1–§7.7.2).
#:
#: ``curve`` reads the declared rate off the whitepaper's decay formula.
#: ``supersede-only`` holds retained relevance whole until the row's
#: supersession event, because the class has no curve to read. The two members
#: name two SDK code paths — the :data:`ArtifactRole` / :data:`RegistrationMode`
#: shape, and their reason — and no deployment can add a third. Which of its
#: observation types takes which path is the deployment's to declare, in its
#: table, beside every rate.
DecayMode = Literal["curve", "supersede-only"]

#: WHICH OF AN OBSERVATION'S TWO INSTANTS a λ_c row decays against
#: (``D-IMPL-331``).
#:
#: ``observed-at`` reads :attr:`ccf.halflife.decay.Observation.observed_at` —
#: when **the fabric learned** the claim. ``valid-from`` reads
#: :attr:`~ccf.halflife.decay.Observation.valid_from` — when **the source**
#: says it observed the thing.
#:
#: **They are different questions and the table has to say which one it means.**
#: :meth:`ccf.assembly.worker.AssemblyWorker._stitch` sets a claim's
#: ``observed_at`` to ingestion *always*, by design, and routes the source's
#: own instant to ``valid_from``. So a table decaying against ``observed-at``
#: measures fabric-learning latency, which for a fabric populated inside the
#: run is zero for every claim however old the underlying observation is.
#: Measured at `cp-09` before this field existed: ``F = 1.000000`` on a serve
#: carrying three observations 65,100 seconds old against their own declared
#: 86,400-second half-life (`CP09-F-06`).
#:
#: **The default is** ``observed-at`` **and it is hash-transparent**, so every
#: table written before this field existed keeps its identity and its `F`
#: unchanged. A deployment whose sources carry real observation times declares
#: ``valid-from`` per row, beside the rate.
DecayBasis = Literal["observed-at", "valid-from"]

#: HOW FRESHNESS AGGREGATES OVER A SET OF OBSERVATIONS OF THE SAME THING
#: (``D-IMPL-333``).
#:
#: ``series-mean`` scores every observation and averages them. That is the
#: right question for a point-in-time product, where each row is a separate
#: thing the fabric knows, and it is the behavior every table had before this
#: field existed.
#:
#: ``leading-edge`` scores ONLY the newest observation in each logical series,
#: as of the decision instant. **A set of observations of one thing has a
#: leading edge, and freshness is a property of that edge rather than of the
#: set's mean.** Dave's framing, and the reason this field exists: *"Age makes
#: a current observation stale. Age does not make historical evidence stale."*
#:
#: **Neither existing mode could express it, measured.** A product carrying two
#: years of daily observations under a one-day ``curve`` scores ``F ≈ 0.007``
#: — the archive's length, not the answer's currency. The same rows under
#: ``supersede-only`` score ``F = 1.000000`` even when the leading edge went
#: cold months ago, because ``supersede-only`` changes each observation's VALUE
#: and never the SET that is averaged. Both are wrong, in opposite directions,
#: for every product that deliberately reads history.
#:
#: The default is ``series-mean`` and it is hash-transparent, so every table
#: written before this field existed keeps its identity and its ``F``.
FreshnessAggregation = Literal["series-mean", "leading-edge"]


class HalfLifeEntry(CCFContract):
    """One row of a λ_c table (whitepaper §7.7.1–§7.7.2; INV-CH7-59).

    The whitepaper's illustrative table is four columns wide — observation
    type, λ_c band, dominant decay driver, supersession event — and the *row
    shape is the commitment*. The driver and the supersession event are not
    documentation: supersession is a Policy event that collapses the decay
    curve rather than continuing it (INV-CH7-60), and an entry that never
    names its supersession event cannot participate in that mechanism later.

    **Two decay modes** (ledger row ``24.5-L-22``, an additive reshaping under
    ``D-10``). Whitepaper §7.7.2 gives one class of observation an
    *event-driven* λ_c rather than a band: a restatement rewrites a closed
    period, so its relevance is whole until the superseding event arrives and
    zero for current-value queries afterward — it supersedes; it does not
    decay. Before this row the table could not say that. ``half_life_seconds``
    was required and positive, and ``supersession_event`` rode *beside* a
    curve, never *instead of* one, so a deployment holding such a class had to
    invent a positive number the specification never gave (a domain value
    minted by a build) or omit the row and record the gap. It chose the gap.
    ``decay`` closes it:

    * ``"curve"`` (the default, so every existing document validates
      unchanged): the row is the four-column row it always was, and
      ``half_life_seconds`` is **required and positive** — a missing rate is
      still refused, because no default rate exists (INV-CH7-58, D-IMPL-38).
    * ``"supersede-only"``: the row declares its driver and its supersession
      event and **no rate**. A number beside ``supersede-only`` is refused
      outright rather than ignored: a field the reader never consults is a
      second, unused copy of a calibration, and an unused field is exactly the
      shape ``24.5-L-23`` was cut to avoid.

    The mode is read by :func:`ccf.halflife.decay.decay_mode_of`; the curve
    reader :func:`ccf.halflife.decay.half_life_of` refuses to hand a curve for
    a supersede-only class rather than fabricate one. No value lives here in
    either mode — which classes supersede is the deployment's to say, as much
    as which classes decay at what rate (CLAUDE.md §11).

    Attributes:
        decay: ``"curve"`` or ``"supersede-only"``, as above.
            Hash-transparent at ``"curve"`` (``D-IMPL-243``): a curve entry
            is the only pre-phase entry, so the field is omitted from the
            canonical form at that value — a table's content-hash version
            is what it was — and ``"supersede-only"`` is rendered.
        half_life_seconds: λ_c as whole seconds under ``curve``. Integer
            rather than a fractional quantity because seconds are exact and
            floats are not; sub-second half-lives are outside the bands the
            whitepaper's operational story contemplates. Absent under
            ``supersede-only``. Hash-transparent at ``None`` under
            ``D-IMPL-243`` amendment 2: ``None`` occurs only on a
            supersede-only entry, and an entry that carries no rate is
            omitted-at-sentinel exactly as the required-seconds shape of
            ``13bd250`` rendered nothing for it; a curve entry's seconds
            are rendered as they always were.
        decay_driver: What actually makes this observation type go stale.
        supersession_event: The event that ends this observation's validity for
            current-value queries. Required in both modes — under
            ``supersede-only`` it is the *only* thing that ends it.
        decay_basis: WHICH INSTANT this row decays against (``D-IMPL-331``) —
            :data:`DecayBasis`. ``observed-at`` (the default, and
            hash-transparent, so every table written before this field existed
            is byte-identical and scores identically) measures how long ago the
            FABRIC learned the claim. ``valid-from`` measures how long ago the
            SOURCE observed it, and is what a row whose class decays *in the
            world* declares. A row declaring ``valid-from`` for an observation
            carrying no ``valid_from`` is **refused by name** rather than
            falling back: a silent fallback to ``observed_at`` would report a
            perfectly fresh figure for a claim whose age nobody knows, which is
            the defect this field exists to end.
        freshness_over: HOW freshness aggregates over observations of the same
            thing (``D-IMPL-333``) — :data:`FreshnessAggregation`.
            ``series-mean`` (the default, hash-transparent) scores every
            observation and averages. ``leading-edge`` scores only the newest
            observation in each logical series as of the decision instant, and
            is what a product carrying history declares: *age makes a current
            observation stale; age does not make historical evidence stale*.
        series_key_attribute: WHICH CLAIM ATTRIBUTE names the logical series,
            for ``leading-edge`` only. ``None`` — the default — means the whole
            observation type is one series. A deployment whose type carries
            several independent series (one per bond, one per account) names
            the attribute that distinguishes them, exactly as the policy
            operator's ``classification_attribute_by_class`` names the
            attribute it admits on: the SDK cannot know what a deployment
            considers one series, so the deployment says.

            **THE NAMED ATTRIBUTE MUST BE A FIRST-CLASS CLAIM ATTRIBUTE.**
            :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` resolves this
            name against ``claim.attributes``, so a partition key that lives
            only inside a serialized blob — a ``payload_json`` column, a nested
            document — is invisible to the scorer. It does not raise. The key
            resolves to ``None``, every observation of the type lands in one
            series, and ``leading-edge`` keeps a single observation where it
            should have kept one per series. **The failure is silent and reads
            as a working configuration**: the table validates, the product
            serves, and ``F`` is simply computed over the wrong set.

            The concrete case, from ``examples/cp-10-rating-and-spread-migration``
            (rung 10): ``rsm_spread`` declares
            ``series_key_attribute: instrument_id`` because each bond is its own
            spread series. ``instrument_id`` is carried in that node's
            ``raw_payload`` *and* listed in its resolution rule's
            ``attribute_keys``, so it reaches the claim. Left only inside that
            example's ``payload_json``, all 996 of one obligor's spread
            observations would collapse into a single series and the two bonds
            would share one leading edge.

            The general rule, and it is the same one
            ``classification_attribute_by_class`` obeys: **an attribute a
            control plane document names must be an attribute the claim
            carries.**
    """

    decay: DecayMode = Field(default="curve", json_schema_extra={HASH_TRANSPARENT_KEY: True})
    decay_basis: DecayBasis = Field(
        default="observed-at", json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    freshness_over: FreshnessAggregation = Field(
        default="series-mean", json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    series_key_attribute: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    half_life_seconds: int | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    decay_driver: str
    supersession_event: str

    @model_validator(mode="after")
    def _shape_matches_mode(self) -> "HalfLifeEntry":
        """The rate is present exactly when the mode reads one.

        Replaces the unconditional ``_rate_is_positive`` field validator; the
        two ``curve`` refusals keep that validator's meaning, and the second
        keeps its message verbatim, so every test that pinned it still pins it.
        """
        if self.decay == "curve":
            if self.half_life_seconds is None:
                raise ValueError(
                    "a curve class declares its rate; no default rate exists"
                    " (INV-CH7-58, D-IMPL-38)"
                )
            if self.half_life_seconds <= 0:
                raise ValueError("half_life_seconds must be positive")
        elif self.half_life_seconds is not None:
            raise ValueError(
                "a supersede-only class carries no curve; a number beside it"
                " is a second, unused field (24.5-L-22)"
            )
        if self.series_key_attribute is not None and self.freshness_over != "leading-edge":
            raise ValueError(
                "`series_key_attribute` names how to group a series for"
                " `freshness_over: leading-edge`, and this row aggregates as"
                f" {self.freshness_over!r} — the key would be read by nothing"
                " (D-IMPL-333)"
            )
        return self


class HalfLifeTable(VersionedArtifact):
    """The per-observation-type λ_c table, as a versioned artifact (INV-CH7-58).

    The table ships empty of rows by design: ``entries`` has no default, so a
    deployment that registers no calibration gets a registration failure rather
    than a fabric that decays everything at a rate the SDK picked. λ_c "is
    domain-specific" and the whitepaper's own values are "illustrative, not
    empirical" — the SDK's contribution is this shape and the curve in
    :mod:`ccf.halflife.decay`.
    """

    entries: Mapping[str, HalfLifeEntry] = Field(min_length=1)


class DebtProfile(VersionedArtifact):
    """A decision class's D_c calibration (whitepaper §7.7 CAR; INV-CH7-65).

    Three declared values, none with a default:

    * ``risk_sensitivity`` — the ``λ_c × Risk Sensitivity`` Freshness Budget
      multiplier for this class.
    * ``forced_llm_threshold`` — D_c above which the assessment is routed to
      Forced LLM: "context is partial or stale; the LLM must be invoked with
      explicit awareness of the debt."
    * ``fail_closed_threshold`` — D_c above which the class fails closed rather
      than deciding at all. The whitepaper's conservative bias is architectural:
      elevated debt "biases urgency upward, not downward", so this band exists
      to escalate, never to smooth.

    The fail-closed band must sit at or above the Forced-LLM band; a profile
    that inverts them describes a class that fails closed *before* it escalates,
    which is not a stricter policy but an incoherent one.

    Thresholds are :class:`~decimal.Decimal` in ``[0, 1]``, matching the D_c
    codomain, and are refused as floats upstream by the loader.

    A fourth declared value, ``signal_obligations``, says what each routing
    state *obliges* the deployment to do (D-IMPL-112 gap 3, D-IMPL-117;
    SDK-defined per CLAUDE.md §11). It belongs here because the calibration
    already lives here: this artifact owns the two bands that decide which state
    a decision lands in, and it is already version-pinned per agent, so putting
    the binding anywhere else would split one calibration across two documents
    and two version lanes.

    **The SDK owes the binding and none of its content.** Each entry names a
    routing state — a type the SDK owns, ships and validates — and one opaque
    reference the SDK never parses, never checks against a permitted set and
    never acts on. Which operational duty a decision class attaches to a state
    is user configuration; a list of duty names in this file would be the
    CLAUDE.md §11 defect, and ``D-IMPL-117`` says so directly:
    *"a signal-to-obligation binding that survives replay, and owes no
    obligation vocabulary (that is user configuration ...)"*.

    Unlike the three numbers it does carry a default, and the default is the
    named positive sentinel rather than a value nobody chose: a profile that
    binds nothing asserts so, which is exactly what every profile written before
    this field existed was already asserting (D-IMPL-38).
    """

    risk_sensitivity: Decimal
    forced_llm_threshold: Decimal
    fail_closed_threshold: Decimal
    signal_obligations: SignalObligations = NO_SIGNAL_OBLIGATIONS

    def obligation_for(self, signal: DebtSignal) -> str:
        """The obligation this profile binds to ``signal``, or the sentinel.

        The *extract* half of what D-IMPL-117 says the SDK owes, and the whole
        of it: the caller receives one reference and decides what to do with it,
        because deciding here would be deciding what an obligation means.

        Returns the reference bound to ``signal``, or
        :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE` when no binding
        covers it — never a neighbour's obligation, and never an error. A
        partly-bound profile is the ordinary case rather than a defect, so an
        unbound state resolves to the positive claim that nothing was bound.

        Resolved from *this* profile instance, which is a resolved, versioned
        artifact the caller pinned. Nothing here reaches the Control Plane for a
        "latest" — that is precisely the substitution D-IMPL-26's exact-version
        rule forbids, and it is why the resolved value travels on the product
        rather than being looked up again at replay.
        """
        for binding in self.signal_obligations:
            if binding.signal == signal:
                return binding.obligation_ref
        return NO_OBLIGATION_IN_FORCE

    @field_validator("risk_sensitivity")
    @classmethod
    def _sensitivity_is_positive(cls, value: Decimal) -> Decimal:
        if value <= _ZERO:
            raise ValueError("risk_sensitivity must be positive")
        return value

    @field_validator("forced_llm_threshold", "fail_closed_threshold")
    @classmethod
    def _threshold_is_in_the_debt_codomain(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("debt thresholds must lie in [0, 1]")
        return value

    @model_validator(mode="after")
    def _bands_are_ordered(self) -> "DebtProfile":
        if self.fail_closed_threshold < self.forced_llm_threshold:
            raise ValueError(
                "fail_closed_threshold must be at or above forced_llm_threshold:"
                " a class cannot fail closed before it escalates"
            )
        return self


#: Both path flavours, so one document is admissible on every platform or on
#: none.
#:
#: A manifest is a content-hashed Control Plane artifact, and "is this
#: deployment admissible" must not be a property of the machine that parsed it.
#: The two flavours disagree about what *absolute* means: ``/etc/passwd`` is
#: absolute to :class:`~pathlib.PurePosixPath` and merely rooted to
#: :class:`~pathlib.PureWindowsPath`, which wants a drive; ``C:\secrets`` is
#: the reverse, and ``..\..\x.yaml`` is a single ordinary filename to POSIX
#: and two parent segments to Windows. Asking both and refusing if *either*
#: reads the value as leaving the directory is what makes the refusal
#: platform-invariant.
_PATH_FLAVOURS = (PurePosixPath, PureWindowsPath)


def _leaves_its_own_directory(value: str) -> bool:
    """True when ``value`` names something outside the directory it sits in.

    Three shapes, each asked of both flavours in :data:`_PATH_FLAVOURS`:
    absolute (``pathlib`` discards the directory a relative path was joined to
    when the other side is absolute, so ``root / "/etc/passwd"`` *is*
    ``/etc/passwd``), rooted-or-drive-qualified (``\\etc`` and ``C:etc`` are
    neither absolute nor contained), and any ``..`` segment (``a/../../b``
    normalizes out of the directory even though it starts inside it).

    This is a **syntactic** question about the declaration, decidable from the
    string alone and therefore answerable at the contract boundary where it
    belongs (CLAUDE.md §11 — validation is at the boundary, never deferred). It
    is deliberately not the whole answer: a path that is a plain name can still
    resolve outside through a symlink, which no string inspection can see.
    :func:`~ccf.deployment.manifest.load_and_boot` closes that at the read,
    against the resolved root.
    """
    for flavour in _PATH_FLAVOURS:
        candidate = flavour(value)
        if candidate.is_absolute():
            return True
        if candidate.root or candidate.drive:
            return True
        if ".." in candidate.parts:
            return True
    return False


class ReplayBinding(VersionedArtifact):
    """Where one deployment's decision records go, and under which classes.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11). Whitepaper §7.8
    makes the Control Plane the plane that declares what the fabric is
    permitted to do and the plane its decisions are audited against; it fixes
    nothing about where a deployment's replay artifacts are filed. CLAUDE.md
    §7.4 does: replay records are an ArtifactStore artifact class, and the
    store is a substrate reached through mechanism. This class is the third
    place those two facts meet — the deployment's own binding, declared rather
    than passed.

    The ruling of record is ``D-IMPL-282`` ``R-12`` option 2a (Dave,
    2026-09-08): the ``replay:`` Control Plane section supplies defaults,
    explicit constructor arguments override the declaration, and *"the declared
    binding must actually be consumed and exercised; declaration-only is
    insufficient."*

    Three declared values, none with a default:

    * ``record_class`` — the artifact class every decision record for this
      deployment is filed under, served and refused alike.
    * ``query_pin_class`` — the class the executed-query bytes are filed under.
    * ``store_dirname`` — a contained relative directory the file-backed
      reference store roots at, under a root the caller supplies.

    **Binding only. No product-specific replay semantics.** The same ruling:
    *"No product-specific replay semantics in the Control Plane—only deployment
    binding/configuration."* That is why there is no room here for a record
    shape, a retention rule, a redaction policy or a per-product lane, and why
    the closure is a property of the contract rather than of this paragraph:
    ``extra="forbid"`` is inherited from :class:`~ccf.contracts.base.CCFContract`,
    so a fourth key is refused at parse with the key named.

    **What a declaration can bind, and what it cannot.** ``store_dirname`` is a
    directory name joined onto a caller-supplied root, so the store a
    declaration can select is the file-backed reference implementation,
    :class:`~ccf.artifacts.file_store.FileArtifactStore`. A deployment on
    :class:`~ccf.artifacts.mcp_store.McpArtifactStore` reaches its store by
    passing ``artifact_store`` to
    :func:`~ccf.products.resolver.build_governed_resolver` explicitly, which
    wins under the ruled precedence and is therefore unaffected by anything
    here. That is a limitation of the declaration, stated so the next reader
    finds it rather than discovers it.

    **The dirname is contained, and containment is checked here.** An absolute
    path, a rooted or drive-qualified name, or any ``..`` segment would let a
    Control Plane document address a location outside the root its caller
    chose, which is a document deciding something the deployment's operator did
    not. Refused by name, never normalized: only the author of the declaration
    knows what they meant. The question is asked through
    :func:`_leaves_its_own_directory` — the same predicate
    :attr:`ManifestEntry.path` is held to — so the SDK has one answer to *"does
    this declared name stay inside the directory it was given"* rather than two
    that can drift.

    Attributes:
        record_class: The artifact class decision records are filed under.
        query_pin_class: The artifact class executed-query bytes are filed
            under.
        store_dirname: A contained relative directory under a caller-supplied
            root.
    """

    record_class: str
    query_pin_class: str
    store_dirname: str

    @field_validator("store_dirname")
    @classmethod
    def _dirname_stays_under_its_root(cls, value: str) -> str:
        if _leaves_its_own_directory(value):
            raise ValueError(
                f"store_dirname {value!r} names something outside the root it"
                " is joined to (it is absolute, rooted, drive-qualified, or"
                " carries a '..' segment); a Control Plane document declares a"
                " contained relative directory, never a location on a"
                " particular disk"
            )
        return value


#: The v0 constraint vocabulary (``D-IMPL-253`` Q5, Dave: *"maximum, minimum,
#: allowed_set, required, preferred is a good v0 vocabulary. preferred must
#: remain non-refusing guidance."*). Five members and no sixth. The first three
#: are restrictiveness on three different axes — a numeric ceiling, a numeric
#: floor, and a set intersection — which is why "most restrictive wins" is a
#: comparison *within* a comparable family and never a fold across the
#: vocabulary (Q4).
ConstraintOperator = Literal[
    "maximum", "minimum", "allowed_set", "required", "preferred"
]

#: The same five members, closed by value. Derived from the ``Literal`` rather
#: than restated, so the vocabulary cannot drift into two spellings — the
#: :data:`~ccf.skills.catalog.SKILL_TYPES` precedent.
CONSTRAINT_OPERATORS: Final[frozenset[str]] = frozenset(get_args(ConstraintOperator))


class ConstraintApplicability(CCFContract):
    """Which requests a policy constraint reaches (SDK-defined; CLAUDE.md §11).

    Whitepaper §7.8 makes the Control Plane the holder of policy; it does not
    specify how a policy narrows to a request. ``D-IMPL-251`` names the axes
    the resolver is given — product class, tenant, principal/perspective,
    intent — and this is those axes as data.

    **``None`` means *any*, and it is a statement rather than a gap.** A
    constraint that names no tenant applies to every tenant, which is the
    ordinary shape of an enterprise-wide rule; a constraint that names one
    applies to that one. The four members are conjunctive: every axis a
    constraint *does* name must match for the constraint to apply. Each is
    hash-transparent at ``None`` (``D-IMPL-243``), so an applicability that
    narrows nothing renders as the empty statement it is.

    The SDK validates none of the values. A product class id, a tenant id, a
    perspective role and an intent are all the deployment's vocabulary
    (CLAUDE.md §6.4, CINV-01); this contract owns the four *axes* and none of
    their content.

    Attributes:
        product_class: The product class this constraint governs, or ``None``
            for every class.
        tenant: The tenant it governs, or ``None`` for every tenant.
        perspective_role: The Π role-conditioning it governs (whitepaper §7.5),
            or ``None`` for every role.
        intent: The request intent it governs, or ``None`` for every intent.
    """

    product_class: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    tenant: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    perspective_role: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    intent: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class PolicyConstraint(VersionedArtifact):
    """One governed boundary on one request parameter (whitepaper §7.8).

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11). §7.8 makes the
    Control Plane the place where the fabric's permitted behavior is declared
    and the plane decisions are audited against; it does not specify a
    parameter-level constraint artifact. ``D-IMPL-251`` and ``D-IMPL-253`` Q3
    do, and Q3's ruling is the reason this is a class of its own: *"A policy
    constraint has independent identity, version, effectivity and authority and
    should not disappear inside another bundle."*

    **It lives in no other bundle, and it is never a field of**
    :class:`ProductClassDeclaration`. ``D-IMPL-251``, in Dave's words: policy
    limits are not placed in product-class registration *"because then you lose
    the ability to answer: is this a property of the product, or a rule imposed
    by a particular policy regime? That distinction matters for audit, replay,
    and reuse."* A product's own preference is a **default**, declared on
    :class:`~ccf.products.request.ProductRequestContract`; a governed boundary
    is this, and the two resolve independently
    (:mod:`ccf.products.provenance` is the record that keeps them apart).

    **``preferred`` is guidance the resolver never refuses on** (``D-IMPL-253``
    Q5: *"preferred must remain non-refusing guidance"*). That property cannot
    be a validator here — a validator sees one artifact and refusal is a
    property of a *resolution* — so **the resolver enforces it, not this
    class**, and it is stated here so that a reader of the vocabulary does not
    mistake the fifth member for a fifth boundary. The same holds for
    ``priority``, which orders comparable constraints and, per Q4, *"must never
    erase an applicable hard constraint."*

    **Effectivity is evaluated at the request's own instant, never at "now"**
    (``D-IMPL-253`` Q6: *"otherwise replay of the same historical decision can
    resolve a different policy"*). This class carries the window; the resolver
    compares it against ``asked_at``. Both instants are timezone-aware because
    :func:`load_artifact` refuses a zone-less timestamp before this contract
    ever sees one (``D-IMPL-38``: no implicit UTC).

    **This class declares shape and no content.** There is no parameter name,
    no threshold and no policy id in this module: which parameter a regime
    bounds, at what value, on whose authority, is the deployment's declaration
    (CLAUDE.md §6.4, CINV-01).

    Attributes:
        policy_id: The regime this constraint belongs to. Several constraints
            may share one ``policy_id`` and each remains its own artifact under
            its own key with its own content-hash version — which is what
            *"should not disappear inside another bundle"* buys.
        applies_to: The axes this constraint narrows to.
        parameter: The request parameter it bounds, by the name the product
            class's request contract declares.
        operator: Which comparison it expresses, from
            :data:`CONSTRAINT_OPERATORS`.
        value: The boundary's value, and the type follows the operator:
            ``maximum``/``minimum`` take a :class:`~decimal.Decimal`,
            ``allowed_set`` a non-empty tuple of names, ``required`` takes
            ``None`` (the constraint is that the parameter be present at all),
            and ``preferred`` takes a decimal or a name. A quoted number under
            ``maximum``/``minimum`` is read as a decimal, because the operator
            makes the numeric reading unambiguous; floats never arrive at all
            (:func:`load_artifact` refuses them).
        overridable: Whether an entitled principal may override this
            constraint. ``False`` — the default — is the safe reading of
            ``D-IMPL-251``: *"Policy constraints may not be overridden unless
            the policy explicitly says they are overridable."* Naming the
            policy is not sufficient authority to exercise the override; the
            resolver must also establish entitlement (``D-IMPL-253`` Q7).
            Hash-transparent at ``False``.
        source_authority: Who imposed it — a regulator, a jurisdiction, an
            enterprise body. Opaque prose the SDK never parses and never checks
            against a permitted set, in the same voice as
            :attr:`DebtProfile.signal_obligations`' obligation references.
        effective_from: The instant this constraint begins to apply.
        effective_until: The instant it stops applying, or ``None`` for a
            constraint with no stated end. Hash-transparent at ``None``.
        reason: The declared justification or citation. Recorded on the
            artifact, and carried onto every
            :class:`~ccf.products.provenance.ParameterBound` this constraint
            establishes, so the internal resolution and the replay record name
            why the bound was in force (``D-IMPL-260`` P-G). Whether a consumer
            sees it is the Disclosure layer's decision: below ``full`` the
            bound crosses without its ``reason``, ``source`` and ``policy_id``
            (:data:`~ccf.products.disclosure.SUPPRESSED_BELOW_FULL`).
        priority: Ordering among comparable constraints. ``0`` — the default —
            is the positive assertion that this constraint claims no ordering.
            Hash-transparent at ``0``.
    """

    policy_id: str
    applies_to: ConstraintApplicability
    parameter: str
    operator: ConstraintOperator
    value: Decimal | str | tuple[str, ...] | None
    overridable: bool = Field(
        default=False, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    source_authority: str
    effective_from: datetime
    effective_until: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    reason: str
    priority: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: True})

    @model_validator(mode="before")
    @classmethod
    def _a_numeric_operator_reads_its_value_as_a_decimal(cls, data: object) -> object:
        """Let the operator decide how a quoted number is read.

        A Control Plane document quotes its numbers, because a YAML float is
        refused outright (:func:`_reject_floats`) — so a ceiling authored as
        ``"0.20"`` arrives here as text. On a field typed exactly
        :class:`~decimal.Decimal` Pydantic would parse it; on this union it
        would stay a string, and the operator check below would then refuse a
        document that is correct as written.

        So the *operator* drives the parse, and only where the numeric reading
        is unambiguous: ``maximum`` and ``minimum`` are comparisons on a
        numeric axis and cannot mean anything else. ``preferred`` is left
        alone — it admits a decimal or a name, and guessing between them would
        be the silent repair this module refuses everywhere else. A string that
        is not a number is left alone too, so the refusal a reader gets names
        the operator/value disagreement rather than a decimal-parse failure.
        """
        if not isinstance(data, Mapping):
            return data
        if data.get("operator") not in ("maximum", "minimum"):
            return data
        value = data.get("value")
        if not isinstance(value, str):
            return data
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            return data
        return {**data, "value": parsed}

    @model_validator(mode="after")
    def _the_value_matches_the_operator(self) -> "PolicyConstraint":
        if self.operator in ("maximum", "minimum"):
            if not isinstance(self.value, Decimal):
                raise ValueError(
                    f"operator {self.operator!r} bounds a numeric axis and its"
                    " value must be a decimal, quoted in the document so it"
                    f" never parses as a float; got {type(self.value).__name__}"
                )
            if not self.value.is_finite():
                raise ValueError(
                    f"operator {self.operator!r} takes a finite value: a"
                    " non-finite bound is not a bound"
                )
        elif self.operator == "allowed_set":
            if not isinstance(self.value, tuple) or not self.value:
                raise ValueError(
                    "operator 'allowed_set' takes a non-empty list of names:"
                    " an empty set admits nothing and is a constraint no"
                    f" request can satisfy; got {type(self.value).__name__}"
                )
        elif self.operator == "required":
            if self.value is not None:
                raise ValueError(
                    "operator 'required' constrains presence and not value, so"
                    " it takes no value; state the value under 'maximum',"
                    " 'minimum' or 'allowed_set' instead"
                )
        elif not isinstance(self.value, (Decimal, str)):
            raise ValueError(
                "operator 'preferred' is non-refusing guidance and takes a"
                f" decimal or a name; got {type(self.value).__name__}"
            )
        return self

    @model_validator(mode="after")
    def _the_effectivity_window_is_ordered(self) -> "PolicyConstraint":
        if self.effective_until is None:
            return self
        try:
            ordered = self.effective_until > self.effective_from
        except TypeError as error:
            # One instant states a zone and the other does not. `load_artifact`
            # refuses a zone-less timestamp in a document, so this is only
            # reachable by direct construction — and a window whose two ends
            # cannot be compared is not a window, whichever end is at fault.
            raise ValueError(
                "effective_from and effective_until must both state a"
                " timezone: an effectivity window whose ends cannot be"
                " compared cannot be evaluated at a request's asked_at"
                " (D-IMPL-38, no implicit UTC)"
            ) from error
        if not ordered:
            raise ValueError(
                "effective_until must be after effective_from: a constraint"
                " that stops applying before it starts never applies, which is"
                " a document nobody meant to write"
            )
        return self


class OperatorParametersArtifact(VersionedArtifact):
    """Marker base of every operator-parameters artifact class (whitepaper §7.4).

    Carries no fields of its own. It exists so that the operator-registry builder
    can type its ``parameters`` mapping as
    ``Mapping[str, OperatorParametersArtifact]`` and accept all four canonical
    categories *by type*. Without it the builder would have to ``isinstance``-filter
    four unrelated classes — and that idiom, copied into adopter code to assemble
    the mapping, is precisely the new duplication class this surface exists to
    prevent.

    **No field in this hierarchy carries a default.** Every value is required at
    plan time and must arrive from a Control Plane artifact. A default is a value
    nobody chose, and a value nobody chose cannot be audited, cannot be versioned,
    and silently changes the meaning of a replay when the SDK revises it
    (D-IMPL-38; :mod:`ccf.operators.params`).

    **Why these classes live here and not in** :mod:`ccf.operators.params`. Two
    reasons. ``ccf.operators`` is L4, and an L4 module importing the Control
    Plane's versioned base would invert a layer. And a *subclass* leaves every
    existing direct construction site — tests, perf fixtures, adopter code —
    untouched, which the additive posture of this surface requires.
    """


class TraversalNeighborhoodParametersArtifact(
    OperatorParametersArtifact, TraversalNeighborhoodParameters
):
    """The Traversal category's parameters as a versioned artifact (§7.4).

    Inherits :class:`~ccf.operators.params.TraversalNeighborhoodParameters`
    verbatim, so a parsed artifact **is** a traversal parameter set and passes
    straight to :class:`~ccf.operators.categories.TraversalNeighborhood` with no
    field translation. There is no second vocabulary to drift: the artifact adds
    a semver lane and nothing else.

    No field gains a default here. ``depth_limit`` in particular stays required —
    the bound is the operator's entire correctness claim (INV-CH7-24), and a
    default bound is one nobody chose.
    """


class TraversalDescendantsParametersArtifact(
    OperatorParametersArtifact, TraversalDescendantsParameters
):
    """The Traversal category's DIRECTED walk parameters as a versioned artifact (§7.4).

    The sibling of :class:`TraversalNeighborhoodParametersArtifact` for ledger
    row ``24.5-L-06``, in the same shape: inherits
    :class:`~ccf.operators.params.TraversalDescendantsParameters` verbatim, so
    a parsed artifact **is** a descendants parameter set and passes straight
    to :class:`~ccf.operators.categories.TraversalDescendants` with no field
    translation. The artifact adds a semver lane and nothing else.

    **Selecting this class is what selects the direction.** The document
    carries no ``direction`` value — the operator the builder constructs from
    it (``src/ccf/deployment/operators.py::build_operator_registry``) walks
    forward, subject to object as stored, and no authored value can turn it
    around. A deployment that wants the undirected neighborhood authors the
    sibling class; both are ``traversal`` (D-IMPL-223).

    No field gains a default here; ``depth_limit`` stays required (INV-CH7-24).
    """


class TemporalAsOfParametersArtifact(
    OperatorParametersArtifact, TemporalAsOfParameters
):
    """The Temporal category's parameters as a versioned artifact (§7.4).

    Inherits :class:`~ccf.operators.params.TemporalAsOfParameters` verbatim, so a
    parsed artifact is accepted directly by
    :class:`~ccf.operators.categories.TemporalAsOf`.

    ``require_valid_at_boundary`` keeps no default: which of the bitemporal
    model's two axes a decision needs is a decision-class property, so it is
    declared rather than assumed, and a flag nobody set is a flag nobody chose.
    """


class SimilaritySelectParametersArtifact(
    OperatorParametersArtifact, SimilaritySelectParameters
):
    """The Similarity category's parameters as a versioned artifact (§7.4).

    Inherits :class:`~ccf.operators.params.SimilaritySelectParameters` verbatim —
    ``query``, ``minimum_score_percent``, ``ranked_entity_classes`` — so a parsed
    artifact is accepted directly by
    :class:`~ccf.operators.categories.SimilaritySelect`.

    It declares **two artifact-only fields beyond the operator's contract**, and
    the asymmetry is deliberate rather than an oversight. Both govern
    :class:`~ccf.similarity.protocol.SimilarityIndexProtocol` *construction* —
    the registry builder reads them before the operator exists — and both are
    deliberately **absent** from
    :class:`~ccf.operators.params.SimilaritySelectParameters`, because putting a
    construction-time value on the per-invocation parameter set would make the
    L4 invoke contract carry state no invocation reads. Neither carries a
    default.

    Attributes:
        similarity_corpus_attribute_by_class: ``entity_class -> attribute key``
            naming the attribute whose text forms that class's corpus entry.
            No default: a class absent from this mapping contributes no corpus
            entry, and guessing an attribute name is guessing what a deployment
            meant by "similar".
        index_version: The version identity this deployment assigns to the
            corpus state its index ranks against (INV-CH7-27, ``D-IMPL-38``).
            It reaches
            :attr:`~ccf.similarity.protocol.SimilarityIndexProtocol.index_version`
            and travels from there into ``L`` on every ranked result, so it is
            the token a replay is held against when it asks *which corpus said
            these two names were alike*.

            **This is the value's canonical declarative home, and the
            declaration is its authority** (``D-IMPL-292``, Dave: *"declaration
            owns the version → resolver consumes it → deployment supplies the
            implementation, not an alternate semantic version"*). Until
            ``24.11-02b`` it was a keyword argument to
            ``ccf.deployment.build_operator_registry`` and a field on
            :class:`~ccf.products.resolver.GovernedResolver`, which made a
            decision-affecting semantic value something a deployment restated in
            code at every call site — ungoverned, unversioned, and invisible to
            the pin set. Declared here it is content-hashed into a registered
            artifact, so re-authoring the corpus identity **necessarily** shows
            up as a changed pin in replay dimension 2, where re-authoring a call
            argument showed up nowhere.

            **What the deployment still owns is the implementation.** Which
            :class:`~ccf.similarity.protocol.SimilarityIndexProtocol` backs the
            ranking — token overlap, sqlite-vec, Chroma — is a substrate choice
            and stays the deployment's. What it may no longer do is hand the
            fabric a *different semantic version* than the one it declared: two
            disagreeing values mean two different corpora, and silently
            preferring either makes the determination irreproducible. There is
            therefore exactly one site, not a precedence order.

            No default, for the reason every other field here has none, sharpened
            by what this one is: the SDK cannot mint a corpus identity. A version
            derived from this artifact's own pin would be identical across two
            different corpus boundaries, which is precisely the identity the
            determinism contract exists to distinguish — so the deployment
            assigns it, and an artifact that assigns none is refused at parse
            rather than three frames into a build.
    """

    similarity_corpus_attribute_by_class: Mapping[str, str]
    index_version: str


#: Where a request-bound operator parameter takes its value from.
#:
#: A module-level alias in :data:`DecayMode`'s and :data:`ConstraintOperator`'s
#: shape, and for their reason: this is an SDK **mechanism** token set, not a
#: deployment's vocabulary, so it is declared once where the module declares its
#: other closed sets rather than inline on the field. One member today, named
#: rather than assumed — a second source is then a visible change to this line
#: with its own ruling, instead of a silent widening inside a class body.
RequestBindingSource = Literal["effective_request"]


class RequestBoundParameter(CCFContract):
    """An operator parameter supplied by the governed effective request.

    SDK-defined (CLAUDE.md §11); the ruling of record is ``D-IMPL-295``
    (`24.10-F-11`). The whitepaper's §7.4 operator parameters are Control Plane
    configuration; it does not say how a parameter whose value is only knowable
    *per request* is declared. Before this contract there was no way to say it,
    so a deployment that needed one substituted a value into its own resolved
    artifact at runtime — an ungoverned write to a Control Plane declaration,
    invisible to replay and to the pins.

    **The authority chain this sits at the end of, and it is the whole design:**
    Control Plane policy/default envelope → :func:`~ccf.products.constraints.
    resolve_effective_request` → *this* declared binding → operator. The binding
    is the LAST link and deliberately the dumbest one: it performs no domain
    validation and invents no default, because both already happened upstream
    and doing them again here would create a second authority for one value.
    What it consumes is the effective value that **survived governance**.

    **Not a transform, and the narrowness is the point.** There is no
    expression language, no templating, no substitution syntax, no callback and
    no mapping DSL. The only relationship expressible is *effective request
    parameter → operator parameter*, and the effective value must already
    satisfy the target field's declared type — a mismatch is a wiring defect
    refused when the resolver is built, never coerced. A widening as small as
    scalar-to-singleton is still a transform, and admitting one would make the
    next one arguable.

    **Mutually exclusive with a literal, structurally.** A field that accepts
    this contract accepts it *instead of* its literal value, never beside it —
    the two are variants of one union, so "a literal plus an independent
    binding" cannot be written down. That is what keeps an empty literal
    honest: ``permitted_classifications: []`` continues to mean *admit
    nothing*, and acquires no magical second reading (``D-IMPL-288``,
    Dave: *"Do not preserve the empty-list idiom by making it magical."*).

    Attributes:
        source: Where the value comes from. One member today, spelled out
            rather than assumed, so a second source is a visible schema change
            with its own ruling instead of a silent widening of this one.
        parameter: The request parameter's name, in the deployment's own
            vocabulary. The SDK validates that the request contract declares
            it and that its type fits the target; it judges nothing about what
            the name means (CLAUDE.md §6.4, CINV-01).
    """

    source: RequestBindingSource
    parameter: str

    @field_validator("parameter")
    @classmethod
    def _the_parameter_is_named(cls, value: str) -> str:
        """A blank name is the third state neither variant has a meaning for."""
        if not value.strip():
            raise ValueError(
                "a request-bound operator parameter must name the request"
                " parameter that supplies it; a blank names nothing and would"
                " bind the operator to a value no request can carry"
            )
        return value


class PolicyFilterParametersArtifact(OperatorParametersArtifact):
    """The Policy category's *declarable* parameters (§7.4; D-IMPL-76).

    Alone among the four, this class is **not** a subclass of its operator's
    parameter set. It carries the two fields a deployment can author and omits
    :attr:`~ccf.operators.params.PolicyFilterParameters.permitted_policy_bundle_versions`
    entirely. Both rejected alternatives look reasonable until written down:

    * **Subclass and leave the version set required.** ``params.py`` declares it
      required with no default, so the artifact could never parse — the adopter
      has no value to author, because the value is a content hash minted at
      registration (D-IMPL-76).
    * **Subclass and default it to** ``frozenset()``. Then a parsed artifact
      satisfies ``isinstance(x, PolicyFilterParameters)`` and can be handed
      straight to :class:`~ccf.operators.categories.PolicyFilter` by anyone who
      bypasses the builder — producing an operator that admits *nothing* while
      looking fully configured. That is a silent failure in the other direction,
      and exactly the kind of value-nobody-chose the parameters module refuses.

    A separate, deliberately incomplete contract makes the incompleteness
    *structural*: the type system says this is not an operator parameter set, and
    the operator-registry builder is the only thing that turns it into one, by
    constructing a real
    :class:`~ccf.operators.params.PolicyFilterParameters` with the version set
    taken from the adopter-passed pins. The deployment still names which bundles
    it admits — the SDK only resolves the pin, and the adopter passes it
    (D-IMPL-76).

    Attributes:
        classification_attribute_by_class: ``entity_class -> attribute key``
            carrying that class's classification. Per class rather than one
            global key, because classes carry their sensitivity in their own
            vocabulary — two classes in the same deployment routinely carry their
            sensitivity in differently-named fields. An entity class absent from
            this mapping is inadmissible.
        permitted_classifications: The classification values the principal may
            see. Everything else — *including an entity carrying no
            classification at all* — is excluded: the fabric does not admit state
            it cannot prove is admissible.
    """

    classification_attribute_by_class: Mapping[str, str]
    #: `24.10-F-11` / `D-IMPL-295`: literal **or** request-bound, never both.
    #: A bare sequence is the literal envelope and reads exactly as it always
    #: did — `[]` still means *admit nothing*. A mapping is a
    #: :class:`RequestBoundParameter`, and the resolver replaces it with the
    #: governed effective value before the operator is built. The union is what
    #: makes "a literal plus a binding" unwritable rather than merely
    #: discouraged.
    permitted_classifications: frozenset[str] | RequestBoundParameter


class SignalBatch(VersionedArtifact):
    """A batch of L1 event envelopes, parsed rather than hand-marshalled (§7.1).

    Whitepaper §7.1 (Signal Layer) for what an envelope *is*; this class is the
    SDK-defined parsing seam for a serialized batch of them (CLAUDE.md §6.4).
    ``envelopes`` is typed as :class:`~ccf.signal.envelope.SignalEnvelope`, so
    each mapping in the document is validated into a real envelope by the
    contract itself. That is the whole point: the artifact document adopts the
    SDK's **own** field vocabulary — ``source: {system_id: ...}``,
    ``raw_payload:`` — rather than the SDK growing a second vocabulary to
    accommodate a document's flat keys. A translation removed is one that cannot
    drift; a translation relocated into ``/src`` is the same defect with a better
    address.

    **This is a** ``role: load`` **artifact under D-IMPL-80.** It is parsed and
    validated through the same :func:`parse_artifact` seam as every other class,
    and ``load_and_boot`` hands it back to the caller on the boot result — but it
    is never passed to ``register_typed`` and never appears in the pin set. The
    asymmetry is the interesting part. Registering a batch would content-hash raw
    event data into Control Plane state, and by D-06's own rationale the
    registered artifact set is dimension 2 of the five-dimension Decision Replay
    record (whitepaper §7.10.1). Re-authoring an events file would then change
    "what was in force" exactly as a policy-bundle bump does — which is not what
    an event stream is. Events are what the fabric *observed*; the Control Plane
    is what the fabric was *permitted to do*. D-IMPL-80 makes the distinction an
    explicit, required ``role`` field on each manifest entry rather than a
    property an executor has to infer from the class, and a manifest entry naming
    no ``role`` is refused.

    **Why the batch carries** ``tenant_id``. Every envelope declares its own
    (INV-CH7-16 — no untenanted path), but every event in a batch belongs to one
    tenant, and today that value lives in a *different* document — the ontology
    (``ontology.yaml``) — which D-03 makes closed-world over resolution rules
    only. Carrying it here keeps it authored, once, in the artifact that needs
    it, rather than turning it into a loader argument no artifact records.
    Disagreement between the batch and an envelope is **refused, never
    repaired**: silently stamping the batch's value onto an envelope that omits
    it would put a value nobody authored into the fabric's observation record.

    :class:`~ccf.signal.envelope.SignalEnvelope` and
    :class:`~ccf.signal.envelope.SourceIdentity` are untouched by this class.
    ``raw_payload`` stays opaque to L1 and its keys stay the source system's
    vocabulary; renaming the *container* key in a serialized document says
    nothing about the payload inside it.

    Attributes:
        tenant_id: The one tenant every envelope in this batch belongs to.
        envelopes: The batch itself. ``min_length=1`` because an empty batch is
            an authoring mistake, not an ingestion of nothing.
    """

    tenant_id: str
    envelopes: tuple[SignalEnvelope, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _every_envelope_names_this_tenant(self) -> "SignalBatch":
        disagreeing = sorted(
            envelope.envelope_id
            for envelope in self.envelopes
            if envelope.tenant_id != self.tenant_id
        )
        if disagreeing:
            raise ValueError(
                f"envelopes {', '.join(disagreeing)} name a tenant other than"
                f" the batch's {self.tenant_id!r}; state one tenant per batch"
            )
        return self


class PerspectiveArtifact(VersionedArtifact, Perspective):
    """The Π role-conditioning tuple as a versioned artifact (§7.5).

    Inherits :class:`~ccf.projection.plan.Perspective` verbatim — the same shape
    plan 15-08 used for the operator-parameters classes — so a parsed artifact
    **is** a ``Perspective`` and passes straight into projection invocation with
    no field translation. ``principal_id`` and ``role`` keep the meanings §7.5
    gives them (INV-CH7-43) and land verbatim in replay dimension 4, so a
    decision is re-readable against the viewpoint that produced it.

    The artifact adds a ``semver`` lane and nothing else. There is no second
    vocabulary here to drift from the projection contract, which is the entire
    reason for subclassing rather than declaring two fields that happen to match.
    """


class SeamRefusalBinding(CCFContract):
    """One exception type this product class treats as a governed refusal.

    `D-IMPL-347` B2 (Dave, 2026-09-23): *"Product class first; deployment may
    narrow, not widen. The map is a governed value: exception type → cause /
    error code."*

    **Why this is a declared value and not SDK mechanism.** A2 widened the
    SCOPE at which a typed ``GovernedRefusalRaised`` is honored; it deliberately
    did not widen the TYPE, because the SDK cannot know whether a deployment's
    ``ControlRoomUnreachable`` means *the subject is unavailable* or *this
    deployment is broken*. Only the product knows, so the product says — in an
    artifact, like every other governed value (CLAUDE.md §11).

    **The type is matched, never imported.** :attr:`exception` is compared
    against the raised exception's own ``module.QualName``; nothing here
    resolves a dotted path, so a declaration cannot cause an import and a
    misspelled name simply never matches rather than executing something.

    Attributes:
        exception: The fully qualified ``module.QualName`` of the exception
            type, as Python reports it on the raised value.
        cause: The refusal cause to mint, from
            :class:`~ccf.products.refusal.SubjectUnavailableRefusal`'s own
            closed vocabulary. The product's statement about what the failure
            MEANS, which is the half the SDK cannot supply.
        error_code: The deployment-facing code carried on the minted refusal.
    """

    exception: str
    cause: Literal["nonexistent", "unauthorized", "undisclosed"]
    error_code: str


class ProductClassDeclaration(VersionedArtifact):
    """A product class's authored governance, minus the pin registration mints (§7.6).

    Whitepaper §7.6 (the delivery contract and its class-level governance);
    D-IMPL-31 for the TTL anchor, INV-CH7-55 for the assembly mode, INV-CH7-49
    for the per-class schema lane. This is the artifact an adopter writes; the
    servable :class:`~ccf.products.contract.RegisteredProductClass` is what
    :func:`~ccf.products.contract.register_product_class` returns from it.

    **It deliberately does not declare** ``max_ttl_version``. That pin is minted
    by *registering* the :class:`~ccf.products.contract.MaxTTL` value, and it is
    a content hash of what was registered — the same shape D-IMPL-76 ruled on for
    the policy bundle's admitted-version set. An artifact that declared it would
    be authoring a hash of something it does not contain. This is what keeps
    Gate 3 (TTL bounds) meaningful: the ceiling stays an authored artifact value,
    the pin is *derived* from registering it, and a product's own ``expires_at``
    remains a separately authored number. Gate 3 checks one against the other,
    which is only a check while the two come from independent places.

    **Why the operator set is declared here.** It lives on the product class
    because the product class is already the artifact that declares what the
    product *is*, and the operator set an interpretation requires is a property
    of the product, not of the code computing it.

    **What this field is, under design E2.** It is the Control Plane **claim**
    — the value a deployment transcribes into ``lineage.operators_invoked``,
    and never into ``execution``. The operator set the *projection* reads is a
    second, separately authored document, :class:`ProjectionRequirements`
    (``ccf.projection-requirements``), and the two are held together by
    :func:`ccf.deployment.binder.refuse_operator_set_divergence`, called
    between plan construction and
    :meth:`~ccf.projection.engine.ProjectionEngine.execute`. That binder is
    where **authorable** drift fails: a one-key edit to either document
    produces a refusal, and it refuses rather than repairs, because only the
    author knows which of the two they meant. Gate 2 (lineage strict equality,
    INV-CH7-47) sits downstream of both, and what it verifies is
    **assembly-path integrity** — the claim as transcribed into the Contract
    against the engine's execution of the plan — not whether the claim was
    right in the first place.

    This passage previously asserted that the projection's declaration and the
    engine's resolution were mutually independent. They never were, under any
    design considered: :meth:`~ccf.projection.engine.ProjectionEngine.execute`
    builds ``operators_invoked`` and ``steps`` in one loop over the same
    operator plan, so the engine is a faithful transcriber of the plan rather
    than an independent witness of it. The ruling of record is
    ``docs/DECISIONS.md`` **D-IMPL-86** (Dave, 2026-08-05) together with its
    **correction of 2026-08-05** for where the binder call belongs; CLAUDE.md
    §11 requires an SDK extension to cite this project's own decision record
    rather than the whitepaper. The standing AST guard
    (``tests/products/test_required_operators_guard.py``) still refuses a
    projection that reads the operator registry's own keys — a tripwire over a
    convention list of receivers, not a wall.

    ``min_length=1`` on the operator keys follows the whitepaper's own posture
    rather than an ergonomics preference: §7.6 (*Context Products — System of
    Delivery*) makes the empty-operator guard the first of the three validation
    gates, and its reasoning — stated here in this project's words, because
    CLAUDE.md §11 requires a citation by section number and title and not a
    reproduction of the text — is that resolving no operator at all is evidence
    the graph was never consulted, so a zero-length set reports a
    misconfiguration rather than an assembly that legitimately needed nothing.
    A declaration of zero operators could only ever produce a resolved set of
    zero, which Gate 1 refuses at assembly time. Refusing it here refuses it
    where the author can still fix it. A deployment that serves no product simply
    authors no document of this class — that is a different thing from a product
    class declaring it needs nothing.

    Attributes:
        schema_name: Class identity.
        schema_version: The product class's **own** semver lane (INV-CH7-49),
            which is not the artifact's ``semver`` lane. Two lanes because they
            version different things: how the product's schema evolved, and how
            this declaration document evolved. Lanes are never compared across
            classes.
        ttl_anchor: Declared TTL derivation anchor (D-IMPL-31).
        assembly_mode: Declared assembly mode (INV-CH7-55).
        max_ttl_key: Control Plane key of the class's MAX_TTL artifact. The key
            is authored; the version pinning it is not.
        required_operator_keys: Registry keys of the operators the class's
            interpretation depends on. Order is not significant — the engine
            imposes the dependency order (INV-CH7-28).
        accepted_policy_binding_modes: The **accepted modes** of the
            ``policy_binding`` attestation dimension — an unordered set drawn
            from the closed D-09 vocabulary
            (:data:`~ccf.graph.protocols.PolicyBindingMode`), SDK-defined per
            CLAUDE.md §11. A source whose
            :class:`~ccf.graph.protocols.SourceAttestation` reports a
            ``policy_binding`` mode outside this set is refused for this
            class. These are accepted-mode *sets*, not ordered minima: no
            strength ordering exists between ``assembly-stamped`` and
            ``admission-verified`` (D-09's word "minima" is realized as
            unordered accepted-mode sets). The default —
            ``{"assembly-stamped"}`` — is the positive assertion of the
            tier-1 posture every pre-attestation class already lived under
            (the sentinel-default precedent): consuming a tier-2 source
            requires the class to declare ``admission-verified`` explicitly,
            so tier-2 consumption is deny-by-default until a class opts in
            (D-09). ``peer`` is a reference, not a mode, and carries no
            acceptance set — it is pinned into replay, never ranked.
        accepted_lineage_modes: The **accepted modes** of the ``lineage``
            attestation dimension (:data:`~ccf.graph.protocols.LineageMode`),
            under exactly the discipline of
            ``accepted_policy_binding_modes``: an unordered accepted-mode
            set, defaulting to the tier-1 ``{"graph-supplied"}`` posture, so
            ``product-carried`` lineage is deny-by-default until a class
            declares it (D-09).
        freshness_sla: The §6.3 **Freshness SLA** element, per signal
            (D-IMPL-106 option (b), which ruled it class-level and left the
            per-signal shape to the implementing plan).
        discovery: The §6.3 **Discovery** element — the registry facts a class
            is located by (D-IMPL-98, under which discovery is not
            declaration-only).
        addressability: The §6.3 **Addressability** element, path half only.
            The argument half is D-IMPL-98's typed request contract and is
            deliberately not authored here.
        constituent_validity_floors: D-IMPL-31's declarable floors, ruled
            2026-07-25. Authored here; the refusal that reads them is plan
            ``15.5-12``'s, at assembly, where the mix exists.
        payload_schema_key: Control Plane key of the class's declared payload
            schema (D-IMPL-97 ruling 1). **The key is authored; the version
            pinning it is not** — see the class docstring's rule above, which
            this field is the second instance of.
        request_contract_key: Control Plane key of the class's declared
            **request contract** — the typed surface a caller's question is
            validated against, so that the subject and the instant are
            arguments the caller supplies rather than literals authored in this
            document (D-IMPL-98, option (a)). The **third** instance of the
            authored-key/derived-version rule, and ``request_contract_version``
            is absent for exactly the reason ``max_ttl_version`` and
            ``payload_schema_version`` are. The contract itself is
            :class:`~ccf.products.request.ProductRequestContract`, a separately
            authored ``ccf.product-request-contract`` document that names the
            class and lane it serves, and
            :func:`~ccf.products.request.refuse_request_contract_pin` refuses a
            pin onto the wrong class at wiring time. **Nothing in this tree
            resolves this key at a door yet**: D-IMPL-108 ruled that the
            product-resolver seam is widened exactly once, by plan
            ``15.5-15``, carrying the typed request and the authorized
            perspective together rather than reshaping 24 files twice.

        serve_obligations: What this class declares about serving
            (``24.5-L-14``, ``24.5-L-26``, ``24.6-L-04``). Two members of two
            different kinds. The *obligation* — the payload MEMBERS the class
            names — is a STRUCTURAL declaration the serve path enforces
            through the ONE gate mechanism ``D-IMPL-237`` licenses
            (:data:`~ccf.products.gates.GATE_DECLARED_OBLIGATIONS`): members,
            never a payload shape — ``D-IMPL-238`` reads ``D-IMPL-102`` limb 3
            as *no payload gate*. Products do not declare gate TYPES; they
            declare obligations under the one type the SDK ships. The
            *default* — ``default_debt_tolerance`` — is not enforced by any
            gate: it is the tolerance that applies when the caller states
            none, and a caller's own value is honored as requested
            (``D-IMPL-251`` C1/C2, ``D-IMPL-240`` amendment 2). Its number is
            this document's to author; the SDK holds no number. Defaults to
            :data:`~ccf.products.contract.NO_SERVE_OBLIGATIONS`.
            Hash-transparent at that sentinel (``D-IMPL-243``): a
            declaration obliging nothing is every pre-phase declaration,
            so the field is omitted from the canonical form at that value
            and a declared obligation is rendered and versions the document.

        declared_product_gate: The class's own runtime invariant, by governed
            IDENTITY only (``24.10-02`` / ``R-11``; ``D-IMPL-282`` option 1a
            with ``D-IMPL-224``). The SDK owns the **slot** and none of the
            **value**: which invariant a product declares, under what id and
            at what lane, is the deployment's vocabulary (CLAUDE.md §6.4), and
            nothing in ``src/`` reads either string. What the class declares
            here is *governed*; what it computes is a
            :class:`~ccf.products.resolver.ProductGateProtocol` callable the
            deployment supplies to
            :func:`~ccf.products.resolver.build_governed_resolver`, and the
            two halves stay apart on purpose — a declared gate with no
            supplied callable is refused when the resolver is built, so a
            declared check cannot silently stop checking. This is **not** a
            widening of :data:`~ccf.products.gates.GATE_DECLARED_OBLIGATIONS`
            or of :func:`~ccf.products.gates.run_gates`' sequence (``D-11``,
            ``D-13``). Defaults to
            :data:`~ccf.products.contract.NO_PRODUCT_GATE`, hash-transparent at
            that sentinel for ``serve_obligations``' reason: a class declaring
            no gate is every class already authored, so its content address —
            and therefore its pin — does not move.

    **The eight governance fields above all default**, on the
    ``accepted_policy_binding_modes`` precedent and for the same reason: an
    artifact authored before they existed declared exactly what it declares
    now, so no committed document is rewritten and no adopter's file becomes
    invalid. Each default is a named positive assertion in
    :mod:`ccf.products.contract`, not a blank.
    """

    schema_name: str
    schema_version: str
    ttl_anchor: TTLAnchor
    assembly_mode: AssemblyMode
    max_ttl_key: str
    required_operator_keys: tuple[str, ...] = Field(min_length=1)
    accepted_policy_binding_modes: frozenset[PolicyBindingMode] = frozenset(
        {"assembly-stamped"}
    )
    accepted_lineage_modes: frozenset[LineageMode] = frozenset(
        {"graph-supplied"}
    )
    freshness_sla: FreshnessSLA = UNMEASURED_FRESHNESS_SLA
    discovery: ProductDiscovery = NOT_DISCOVERABLE
    addressability: ProductAddress = NOT_ADDRESSABLE
    constituent_validity_floors: ConstituentValidityFloors = NO_VALIDITY_FLOORS
    payload_schema_key: str = NO_PAYLOAD_SCHEMA
    request_contract_key: str = NO_REQUEST_CONTRACT
    requires: tuple[ChildRequirement, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: `D-IMPL-347` B2 — the exception types THIS product considers a governed
    #: refusal, with what each one means. Empty is the honest default: a class
    #: that declares none converts nothing, which is exactly A2's behavior.
    seam_refusals: tuple[SeamRefusalBinding, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    serve_obligations: ServeObligations = Field(
        default=NO_SERVE_OBLIGATIONS, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    declared_product_gate: DeclaredProductGate = Field(
        default=NO_PRODUCT_GATE, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: `D-IMPL-343` (design §14 R-3b; `D-IMPL-292` applied). The request
    #: parameter that carries this class's DECISION INSTANT, or ``None`` when
    #: the class declares none — the declaration-side home of
    #: :attr:`~ccf.products.resolver.GovernedResolver.decision_instant_parameter`,
    #: which `24.10-F-09` recorded as an architecture question the resolver
    #: keyword left open. A class that declares it here is served with it
    #: whether it is reached through the paved road or through
    #: :func:`~ccf.products.resolver.build_governed_resolver`; a builder call
    #: that states a DIFFERENT value is refused at build, on the `ttl:`
    #: equality shape. Hash-transparent at ``None`` for `requires`' reason: a
    #: class declaring none is every class already authored, so no committed
    #: declaration's content address moves.
    decision_instant_parameter: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ProjectionRequirements(VersionedArtifact):
    """The operator set a projection plan reads its requirements from (design E2).

    SDK-defined; the ruling of record is ``docs/DECISIONS.md`` **D-IMPL-86**
    (Dave, 2026-08-05) and its **correction of 2026-08-05**. CLAUDE.md §11
    requires an SDK extension to cite this project's own decision record rather
    than the whitepaper, because the whitepaper under-determines the question:
    §7.5 is silent on the *provenance* of a plan's operator set and affirmatively
    blesses data-holder plans.

    **What this class is for.** Under design E2 a projection reads the operator
    keys it depends on from **this** artifact, while
    :attr:`ProductClassDeclaration.required_operator_keys` remains the Control
    Plane **claim** — the value that fills ``lineage.operators_invoked`` and
    never ``execution``. Two documents, separately authored, one per side.

    **Why two documents rather than one.** With a single document the two sides
    of Gate 2 (lineage strict equality, INV-CH7-47) are not merely equal in
    practice, they are *identical by construction*:
    ``execution.operators_invoked`` is ``frozenset(declared.required_operator_keys)``
    through five pure transforms with no branch — the declaration feeds
    ``plan.required``; ``plan.required_operators()`` returns it;
    :func:`~ccf.operators.planner.build_operator_plan` resolves each key
    self-keyed, so ``resolve(k).key == k``;
    :class:`~ccf.projection.engine.ProjectionEngine` writes
    ``outputs[operator.key]``; and it returns
    ``operators_invoked=frozenset(outputs)``. Nothing a deployment could author
    would make the two sides diverge. That identity is the finding that reopened
    the question after the first remedy was recorded, and naming it is the whole
    justification for this class's existence.

    **Where drift actually fails.** Not here, and not in the contract: in the
    binder, :mod:`ccf.deployment.binder`, a refusal placed **between plan
    construction and** :meth:`~ccf.projection.engine.ProjectionEngine.execute`,
    which refuses when
    ``frozenset(product_class.required_operator_keys) != frozenset(plan.required_operators())``.
    This class is one half of that comparison's authored input; the product-class
    declaration is the other. The placement is the one D-IMPL-86's **correction
    of 2026-08-05** fixes — D-IMPL-86 element (3) as originally written named a
    placement that cannot exist, because
    :func:`~ccf.deployment.manifest.load_and_boot` has no
    :class:`~ccf.projection.plan.ProjectionPlan` in scope at any of its
    preflights; a plan is adopter code constructed *after* that call returns.
    Cite the correction, never element (3), anywhere this placement is described.

    **The residual, in the ruling's own terms.** A deployment that reads one
    artifact into the other still collapses the binder, so dual authorship
    remains convention-assisted **at the authoring boundary** even though the
    check itself is structural. The correction names a second residual of the
    same family: because the binder is invoked by adopter code, nothing outside
    this project's own ``examples/`` tree holds a deployment to calling it.

    **Why an artifact rather than operator keys in a projection class body.**
    Under the rejected design the compliant state (an author typed the keys) and
    the violating state (an author transcribed them out of the product-class
    artifact) are *textually identical*, so no AST gate can tell them apart —
    the shortcut is undetectable in principle rather than merely unhandled. Code
    constants would also put the CLAUDE.md §6.4 classification of operator keys
    in dispute. E2 satisfies the No-Hardcoding Rule by construction rather than
    by argument: under it there are no operator-key code constants at all.

    Attributes:
        plan_id: Identity of the :class:`~ccf.projection.plan.ProjectionPlan`
            these requirements govern, matching its
            :attr:`~ccf.projection.plan.ProjectionPlan.plan_id`. It exists so
            the document states *which* projection it is for, rather than being
            a naked operator list whose subject is recoverable only from the
            manifest key it happened to be filed under.
        required_operator_keys: Registry keys of the operators the projection's
            interpretation depends on — what its
            :meth:`~ccf.projection.plan.ProjectionPlan.required_operators`
            returns. Order is not significant; the engine imposes the dependency
            order (INV-CH7-28). ``min_length=1`` is the whitepaper's
            empty-operator guard, for the reason
            :class:`ProductClassDeclaration` states in full — it is not restated
            here, because one argument stated twice is one argument that can
            drift.
    """

    plan_id: str
    required_operator_keys: tuple[str, ...] = Field(min_length=1)


#: What a manifest entry declares about the artifact it names (D-IMPL-80).
#:
#: ``register`` puts the artifact into the Control Plane registry and into the
#: pin set the load returns. ``load`` parses and validates it through the same
#: seam and hands it back to the caller, but never registers and never pins it.
ArtifactRole = Literal["register", "load"]

#: Which of the Control Plane's two registration paths an entry travels
#: (D-IMPL-85).
#:
#: ``typed`` routes the artifact through :meth:`register_typed
#: <ccf.controlplane.registry.ControlPlaneRegistry.register_typed>` — class
#: binding, contract validation, content hash, audit.
#:
#: ``versioned`` routes it through :meth:`register_versioned
#: <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>`, which
#: does all of that **plus** the D-05 hash-verified bump check against the
#: author's declared ``artifact_version``.
RegistrationMode = Literal["typed", "versioned"]

#: Characters that make a path a *pattern* rather than a name.
_GLOB_CHARACTERS = ("*", "?", "[")

class ManifestEntry(CCFContract):
    """One artifact a deployment manifest names (SDK-defined; CLAUDE.md §6.4).

    Attributes:
        path: Location of the artifact document, relative to the manifest file's
            own directory.

            Two properties, each held by its own validator so each refusal says
            one thing. **Enumerated, never matched** — see
            :meth:`_path_is_a_name_not_a_pattern`. **Beside the manifest, never
            outside it** — see :meth:`_path_stays_beside_the_manifest`, which
            refuses an absolute path and any ``..`` segment.

            The second is the contract half of a two-part refusal, and the
            halves decide different questions. *Is this a well-formed
            declaration?* is decidable from the string, so it is answered here,
            before any I/O, for every consumer of this contract rather than
            only for the one entry point that reads documents. *Does this
            actually open a file inside the deployment?* is decidable only
            against a resolved root — a plain name can still be a symlink out —
            so :func:`~ccf.deployment.manifest.load_and_boot` answers it again
            at the read. Neither subsumes the other, and the pair is what makes
            that function's ``manifest_path`` promise true rather than
            documented.
        key: The Control Plane key this artifact is in force under, and the key
            it is returned under on the boot result. Unique within a manifest.
        class_id: The artifact class the document is validated against, resolved
            through :func:`~ccf.deployment.classes.resolve_artifact_class`.
        role: ``register`` or ``load`` — **required, with no default**
            (D-IMPL-80, RESOLVED 2026-08-04, Dave).

            ``register`` is what every artifact did before this ruling: into the
            registry, into the pin set. ``load`` is parsed, validated, and
            returned, but never registered and never pinned.

            The distinction exists because registering an artifact
            content-hashes it into Control Plane state, and by D-06's own
            rationale the registered artifact set is dimension 2 of the
            five-dimension Decision Replay record (whitepaper §7.10.1). For a
            signal batch that would mean re-authoring an events file changes
            "what was in force" exactly as a policy-bundle bump does — but
            events are what the fabric *observed*, not what it was *permitted to
            do*.

            **Why no default.** Either default would have the SDK deciding a
            replay-dimension-2 boundary on the adopter's behalf, which is the
            objection :func:`ccf.boot.boot` already raises against every other
            default (D-IMPL-38). An entry naming no ``role`` is refused by the
            contract before anything is read, let alone registered.

            For the one class where the SDK *does* know the answer, the choice
            is additionally held to it by
            :func:`~ccf.deployment.classes.refuse_role_the_sdk_fixes`, which
            runs before any registration. That check lives beside the class
            registry rather than here because it is a property of the class, and
            because this module cannot import ``ccf.deployment`` without closing
            an import cycle.
        registration: ``typed`` or ``versioned`` — **required, with no default**
            (D-IMPL-85, RESOLVED 2026-08-05, Dave).

            It names which of the Control Plane's two registration paths the
            entry travels: :meth:`register_typed
            <ccf.controlplane.registry.ControlPlaneRegistry.register_typed>`, or
            :meth:`register_versioned
            <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>`
            with its D-05 hash-verified bump check.

            **Why no default.** Not the reason ``role`` gives — a different one.
            Either default would have the SDK deciding the *governance path* by
            silence for every entry that omitted it, which is precisely the
            convention-mistaken-for-enforcement failure this phase exists to
            close: a deployment would inherit or lose the bump check without any
            document saying so. And the criterion this field serves — that an
            artifact author need not know which of two paths their class belongs
            to — is only true if the manifest **states** the mode rather than
            inheriting one. An entry naming no ``registration`` is refused by the
            contract before anything is read.

            For the classes where the SDK *does* know the answer, the choice is
            additionally held to it by
            :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes`,
            which runs before any registration. That check lives beside the class
            registry rather than here for the same import-cycle reason ``role``
            records above.

            **That check is class-wide, not role-scoped, and that is
            deliberate.** It runs over every entry including ``role: load``
            ones, which are parsed and returned but never registered — so a
            ``load`` entry naming an author-versioned class must still declare
            ``versioned``, describing a path it will not travel. This is the
            same shape as the field's own no-default rule: a check with an
            exemption is a default wearing a different name, and a
            role-conditional one would make the refusal surface depend on a
            second field, so an entry could be admitted under ``load``,
            re-marked ``register`` in a one-word edit, and only then discover
            that its registration mode was wrong. The description a ``load``
            entry states is the description it would be held to.
    """

    path: str
    key: str
    class_id: str
    role: ArtifactRole
    registration: RegistrationMode

    @field_validator("path")
    @classmethod
    def _path_is_a_name_not_a_pattern(cls, value: str) -> str:
        if any(character in value for character in _GLOB_CHARACTERS):
            raise ValueError(
                f"{value!r} is a glob, and a manifest enumerates. A pattern"
                " would make what was in force a function of directory contents"
                " at boot time, recorded by no artifact. Name the file."
            )
        return value

    @field_validator("path")
    @classmethod
    def _path_stays_beside_the_manifest(cls, value: str) -> str:
        if _leaves_its_own_directory(value):
            raise ValueError(
                f"{value!r} leaves the manifest's own directory, and a manifest"
                " names files beside itself. An absolute path or a `..` segment"
                " makes the artifact set a function of the filesystem outside"
                " the deployment: a `role: register` entry would content-hash"
                " whatever it found into Decision Replay dimension 2, and a"
                " file that failed to parse would carry its contents back in"
                " the load error. Name a path relative to the manifest."
            )
        return value


class SecretReference(CCFContract):
    """The *name* of a credential a deployment supplies — never the credential.

    SDK-defined mechanism (CLAUDE.md §6.4 and §10; D-08). A manifest is
    content-hashed and versioned, so anything written into one is persisted into
    the Control Plane record forever. A credential therefore cannot live here.
    The *reference* to one can, and carrying it is a net improvement rather than
    a lateral move: before this contract a credential travelled as a boot
    argument and nothing in the versioned record said which credential a
    deployment had used, so "safe" and "invisible" were the same posture. A
    named reference is auditable, and replay can pin which reference was in
    force without ever recording what it resolved to.

    Two mechanisms make "a value cannot get in here" structural rather than
    conventional:

    * :func:`~ccf.contracts.canonical.canonical_bytes` **refuses**
      ``pydantic.SecretStr`` outright, so a resolved credential cannot be
      content-hashed into an artifact even by accident. Both fields here are
      plain names, and a resolved value never touches this contract at all — it
      is read at boot into :class:`~ccf.graph.registry.ResolvedSecret` and
      travels from there as a function argument.
    * Resolution is fail-closed. A reference naming a variable that is unset —
      or set to the empty string — is refused rather than read as "no
      credential", because a manifest that names a reference has asserted a
      credential is required.

    :attr:`env_var` is the fact plan 15.4-08 pins into Decision Replay
    dimension 2 through :attr:`ccf.graph.registry.AdapterPin.secret_refs`:
    *which reference was in force*, never what it held.

    Attributes:
        field: The adapter connection-contract field this credential satisfies.
            Refused at load if the adapter the manifest names does not declare
            it as a credential field, so a credential authored against one
            adapter cannot be handed to another.
        env_var: Name of the environment variable holding the value — a name,
            never a value. See the two mechanisms above for what keeps it that
            way.
    """

    field: str
    env_var: str


class DeploymentManifest(VersionedArtifact):
    """The one document naming what a deployment puts in force (D-06).

    SDK-defined mechanism (CLAUDE.md §6.4 and §10): the whitepaper fixes that
    Control Plane artifacts are typed, versioned, and exactly pinned at decision
    time (§7.8, §7.10); it does not specify the document that enumerates them.
    This is that document, and it is itself a content-hashable artifact — so
    "what was this deployment configured to put in force" is answerable by
    reading one versioned thing.

    **The backend is declared as a name only (D-08).** There is no connection
    field of any kind, deliberately: a connection string is a deployment
    *environment* value that
    :func:`ccf.boot.boot` already documents as never persisted, and putting one
    in a versioned, content-hashed artifact would persist it into the audit
    plane. The manifest names the adapter; the caller supplies the settings that
    adapter's own contract declares, and
    :func:`~ccf.deployment.manifest.load_and_boot` refuses loudly if the two do
    not agree. An adapter that needs no connection settings at all takes none —
    the check runs against the adapter's contract, never against a list kept
    here.

    **A credential is named, never held (D-08).** ``backend_secrets`` carries
    :class:`SecretReference` entries: an adapter config field, and the
    environment variable whose value satisfies it. See that class for why the
    reference rather than the value, and for the two mechanisms that make the
    distinction structural rather than conventional.

    **Q3 — where** ``tenant_id`` **lives.** It is carried here, optionally, and
    the caller supplies it when absent. D-03 makes ``ccf.resolution-spec``
    closed-world over resolution rules only, so the value that examples read out
    of an ontology document today has to live somewhere, and the manifest is
    where the deployment's own identity already is. It is *optional* rather than
    required because D-IMPL-05 makes tenancy a first-class runtime axis, and a
    manifest-pinned tenant would stop one manifest serving a multi-tenant
    deployment. Exactly one of the two sources must supply it: the entry point
    refuses both-absent and refuses a conflicting pair, mirroring the
    refuse-to-infer posture :func:`ccf.boot.boot` states in its signature — its
    ``backend`` argument is required and has no default, so a fabric cannot
    infer its own substrate — rather than picking a winner.

    Attributes:
        artifacts: Every artifact in force, enumerated. ``min_length=1`` because
            a manifest naming nothing is an authoring mistake rather than a
            deployment that configures nothing.
        backend: The name of the graph adapter this deployment runs on — the
            adapter, not the connection. A plain lowercase name matching
            ``^[a-z][a-z0-9_]*$``, which is a **shape** rule fixing D-16's
            naming convention without naming a single adapter.

            **Which names exist is not a property of this document.** A manifest
            is a document; which adapters a deployment has installed is a
            property of the deployment that parses it. So membership is checked
            at load, against :func:`ccf.graph.registry.declared_names`, and the
            pattern here constrains only the shape.

            This field carried a fixed six-name ``Literal`` until D-IMPL-93. A
            *generated* list was considered and rejected: generated or not, an
            enumeration of database names in a core file is the thing CLAUDE.md
            §11 forbids. The cost of dropping it is one-directional and accepted
            rather than worked around — a typo is now caught at load rather than
            at parse, and the exported schema no longer completes the name in an
            adopter's editor. What it buys is an error message that can name what
            *is* registered, which the ``Literal`` never could because it listed
            what someone had hard-coded rather than what the deployment has; and
            an adapter that ships as a separate installable distribution with no
            line changing in this repository.
        backend_secrets: The credentials this deployment supplies to its
            adapter, **by reference**. Each entry names an adapter config field
            and the environment variable holding its value; the value itself
            never appears here, and :class:`SecretReference` records the two
            mechanisms that make that structural. Empty — the default — is the
            ordinary case, because most adapters declare no credential field at
            all.

            Resolution happens in
            :func:`~ccf.deployment.manifest.load_and_boot`, which refuses a
            reference the resolved adapter does not declare as a credential
            field, and refuses a reference whose variable is unset or empty
            rather than falling back to an anonymous connection.
        resolution_spec_key: Manifest key of the entity-resolution spec.
        policy_bundle_key: Manifest key of the policy bundle in force.
        tenant_id: The deployment's tenant, when the manifest names it.
        survivor_cap: The D-10 survivor-set size cap in force deployment-wide
            (`GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342). **The value is
            Control Plane configuration; the mechanism ships regardless**
            (CLAUDE.md §11 — mechanism, not values): the engine's cap
            machinery exists whether or not a deployment configures a
            threshold, and no threshold constant exists in ``/src``. ``None``
            — the default, and what an absent field parses to — is the
            positive posture "no cap configured", not an omission.
            :func:`~ccf.deployment.manifest.load_and_boot` threads this value
            onto the boot result for the adopter's
            :class:`~ccf.projection.engine.ProjectionEngine` construction,
            and the value in force pins into Decision Replay dimension 2
            (15.2-08) — a cap change is a manifest change, versioned and
            schema-gated, with an audit trail (T-15.2-27). Deployment-wide by
            decision: the manifest is the versioned Control Plane document
            with existing schema/regeneration machinery, and a
            per-product-class override can arrive later without a contract
            break.
    """

    artifacts: tuple[ManifestEntry, ...] = Field(min_length=1)
    backend: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    backend_secrets: tuple[SecretReference, ...] = ()
    resolution_spec_key: str
    policy_bundle_key: str
    tenant_id: str | None = None
    survivor_cap: int | None = None

    @model_validator(mode="after")
    def _secret_fields_are_unique(self) -> "DeploymentManifest":
        """Each adapter config field is satisfied by exactly one reference.

        The same argument :meth:`_keys_are_unique` makes for artifact keys. Two
        entries naming one ``field`` make "which reference was in force"
        ambiguous, and that answer feeds Decision Replay dimension 2 through
        :attr:`ccf.graph.registry.AdapterPin.secret_refs` — so the ambiguity
        would not stay cosmetic. Refusing it here refuses it at parse, before
        anything reads an environment variable.

        Two entries naming one ``env_var`` under *different* fields are
        permitted, deliberately, and the asymmetry is the same one
        :meth:`_keys_are_unique` draws: one variable legitimately satisfying two
        fields is not ambiguous about anything.
        """
        seen: set[str] = set()
        for reference in self.backend_secrets:
            if reference.field in seen:
                raise ValueError(
                    f"backend_secrets declares the field {reference.field!r}"
                    " twice; each field is satisfied by exactly one reference,"
                    " and a repeated field makes the reference in force at"
                    " decision time ambiguous"
                )
            seen.add(reference.field)
        return self

    @model_validator(mode="after")
    def _keys_are_unique(self) -> "DeploymentManifest":
        """Each key identifies exactly one artifact in force.

        Two entries sharing a ``key`` make ``ResolvedPins.version_for(key)``
        ambiguous and make the boot result's ``artifacts[key]`` order-dependent
        — and both of those feed replay, so the ambiguity would not stay
        cosmetic.

        Duplicate *paths* under different keys are permitted, deliberately: one
        document may legitimately be in force under two names, and nothing about
        that is ambiguous. The asymmetry is a decision, not an oversight.
        """
        seen: set[str] = set()
        for entry in self.artifacts:
            if entry.key in seen:
                raise ValueError(
                    f"manifest key {entry.key!r} is declared twice; each key"
                    " identifies one artifact in force, and a repeated key"
                    " makes both its pin and its parsed artifact ambiguous"
                )
            seen.add(entry.key)
        return self

    @model_validator(mode="after")
    def _boot_pins_name_registered_entries(self) -> "DeploymentManifest":
        """The two keys ``boot()`` needs pins for must be pinnable.

        :func:`ccf.boot.boot` requires a ``(key, version)`` pair for the
        resolution spec and the policy bundle, and those versions come from the
        pin set — which carries ``role: register`` entries only. A manifest
        naming a key that is absent, or present under ``role: load``, therefore
        describes a deployment that cannot boot. Refusing it here refuses it
        before anything is registered, rather than after.
        """
        registered = {
            entry.key for entry in self.artifacts if entry.role == "register"
        }
        for field, key in (
            ("resolution_spec_key", self.resolution_spec_key),
            ("policy_bundle_key", self.policy_bundle_key),
        ):
            if key not in registered:
                raise ValueError(
                    f"{field} names {key!r}, which is not declared as a"
                    " 'register' artifact in this manifest; boot needs a pinned"
                    " version for it and only registered entries are pinned"
                )
        return self


class DeploymentConfig(VersionedArtifact):
    """One authoring document for what `DeploymentManifest` and its ten
    artifacts put in force (`D-IMPL-136`; CLAUDE.md §6.4 and §10).

    SDK-defined mechanism, not whitepaper-derived: the whitepaper fixes that
    Control Plane artifacts are typed and versioned (§7.8) and says nothing
    about how many files an adopter writes to declare them. `D-IMPL-136`
    rules that *"the section name **is** the class"* — a deployment names its
    sections in the vocabulary it already uses (`product_class`, `policy`,
    ...) instead of naming a file, a manifest key and a class id three times
    over — and that *"unknown top-level keys are an error"*, so a typo is
    refused by name rather than three layers down as a missing key.

    **This document parses. It does not derive, materialise, register, or
    boot anything** — that is the loader `16-29` builds over this contract.
    A `DeploymentConfig` instance is the typed, closed-world proof that an
    adopter's `ccf_config.yaml` says exactly what it claims to say; turning
    each section into the SDK artifact it names is a separate concern with
    its own module.

    **The ten reserved section names — `product_class`, `operators`,
    `request_contract`, `resolution`, `half_life`, `debt_profile`, `policy`,
    `policy_constraints`, `default_perspective`, `replay` — are the SDK's slots
    and nothing more.** `policy_constraints` is the ninth (`24.6-L-07`,
    `D-IMPL-253` Q3): a MAPPING of label to constraint body, deriving one
    manifest entry per key exactly as `operators` does, so that each
    constraint keeps its own key, its own content-hash version and its own
    effectivity window instead of disappearing inside a bundle. `replay` is the
    tenth (`R-12`, `D-IMPL-282`): where this deployment files its decision
    records and under which artifact classes — deployment binding, and
    deliberately no replay *semantics* (see :class:`ReplayBinding`).

    **Two counts move together and they are not the same count.** This
    docstring names ten section names; `_RESERVED_SECTIONS` in
    :mod:`ccf.deployment.config` is a nine-entry mapping, because `operators`
    is derived per key rather than from that table. A reader comparing the two
    numbers is comparing two different things on purpose.
    Reserving a section *name* is not a claim on an adopter's class-id
    *namespace*: the SDK still claims exactly one prefix, `ccf.`
    (`D-IMPL-84`), and `src/ccf/deployment/classes.py::resolve_artifact_class`
    — which owns that reservation — is untouched by this class.

    **Two of the ten sections are reserved and uninterpreted
    (`D-IMPL-136` §14.3).** `policy` and `request_contract` bodies are
    adopter-owned: the SDK knows the slot exists and which artifact it
    becomes, and validates none of what is written under it. Typing either
    body against a real contract here would be the SDK validating what it
    has ruled it does not interpret.

    **The other eight SDK-owned sections are typed as open mappings here
    too, for a different reason — do not "tighten" this.** `product_class`,
    `resolution`, `half_life`, `debt_profile`, `default_perspective`, `replay`,
    and each `operators` and `policy_constraints` entry's body are eventually
    validated against the SDK's
    own contracts (:class:`ProductClassDeclaration`, the resolution spec,
    :class:`HalfLifeTable`, :class:`DebtProfile`, :class:`PerspectiveArtifact`,
    the operator-parameter classes) — but not by *this* class. A section body
    is *materialised* into a document that also carries a derived `semver`
    and, for `half_life`, is wrapped under an `entries:` key the section
    itself elides — so a field typed as the eventual contract here would
    demand a `semver` the adopter never writes and an `entries:` key the
    section deliberately omits. `16-29`'s loader validates each materialised
    document through :func:`parse_artifact`, the same seam every other
    artifact class validates through, and that is where a malformed section
    produces an `ArtifactLoadError` naming the class.

    **Deployment-level fields mirror `DeploymentManifest`'s fields of the
    same name, so the two documents cannot drift.** `tenant_id`, `backend`,
    `backend_secrets` and `survivor_cap` carry the same types, the same
    defaults and the same rationale as their `DeploymentManifest` twins —
    see that class's own `Attributes:` block, `D-06`, `D-08` and D-IMPL-05.
    `backend_secrets` carries :class:`SecretReference` entries unchanged: a
    credential never enters this document either.

    **`resolution_spec_key` and `policy_bundle_key` are additional fields
    beyond design spec §4.1's top-level list, ruled onto this contract by
    `D-IMPL-138`(b) (Dave, 2026-08-15).** The measured basis, not a case this
    docstring re-argues: `DeploymentManifest` carries exactly `semver`,
    `artifacts`, `backend`, `backend_secrets`, `resolution_spec_key`,
    `policy_bundle_key`, `tenant_id`, `survivor_cap` — the four fields design
    spec §4.1 omitted are the manifest's own fields, which is field parity
    rather than an added judgement call. `resolution_spec_key` and
    `policy_bundle_key` are **required with no default** on
    `DeploymentManifest`, and HW-1's own manifest sets both, so without them
    on this contract the single-file form cannot construct a valid manifest
    at all and `16-30`'s HW-1 equivalence fixture would be unwritable.
    Design spec §6.3 derives both from the section names (`resolution:` and
    `policy:`) and keeps both **overridable** for a deployment that registers
    several and must name which is in force — `None`, the default, means
    *derive from the section name*, and `16-29` reads them. `backend_secrets`
    and `survivor_cap` are unused by HW-1 and are not load-bearing for that
    fixture, but design spec §10 commits that *"compatibility is absolute"*
    and that the single-file form is an *additional* authoring surface —
    without these two, a deployment whose adapter takes a credential, or
    which has configured a D-10 survivor cap, cannot be expressed in the new
    form. Both carry names, never values (:class:`SecretReference`), so
    neither widens what design spec §9 keeps out: the **connection** stays a
    caller-supplied argument to `load_and_boot`, never a field of either
    document.

    Attributes:
        tenant_id: The deployment's tenant, when this document names it —
            optional for the reason `DeploymentManifest.tenant_id` is
            optional (D-IMPL-05: tenancy is a first-class runtime axis, and a
            document-pinned tenant would stop one document serving a
            multi-tenant deployment).
        backend: The graph adapter's name — a shape rule
            (`^[a-z][a-z0-9_]*$`) naming no adapter, exactly as
            `DeploymentManifest.backend` is. Required: an authoring document
            naming no backend describes no deployment.
        backend_secrets: Credential references this deployment supplies to
            its adapter, by name only. Empty — the default — is the ordinary
            case.
        survivor_cap: The D-10 survivor-set size cap in force
            deployment-wide, or `None` — the default — for "no cap
            configured".
        resolution_spec_key: Which registered key holds the entity-resolution
            spec in force. `None` — the default — means *derive from the
            `resolution:` section name*.
        policy_bundle_key: Which registered key holds the policy bundle in
            force. `None` — the default — means *derive from the `policy:`
            section name*.
        product_class: The `ccf.product-class` section body. **Required** —
            every other section is optional and absent by default,
            distinguishably from an adopter who wrote the heading and
            nothing under it: an absent `policy:` is a deployment declaring
            no regime, an empty one is authored and empty, and `16-29`
            refuses the second.
        operators: Operator-category bodies, keyed by the operator id
            appearing in `product_class`'s `required_operator_keys`. Each
            value is itself an open mapping — the operator's own parameter
            fields — validated in `16-29` against the matching
            `ccf.operator-parameters.*` contract, never here.
        request_contract: The `hw1.request-contract`-shaped reserved section.
            Adopter-owned and uninterpreted (`D-IMPL-136` §14.3): the SDK
            knows the slot exists and supplies the class id and registration
            metadata; it does not own the argument vocabulary.
        resolution: The `ccf.resolution-spec` section body.
        half_life: The `ccf.half-life-table` section body, unwrapped — see
            the class docstring's materialisation note for why this is not
            typed as :class:`HalfLifeTable` here.
        debt_profile: The `ccf.debt-profile` section body.
        policy_constraints: Parameter-level policy constraint bodies, keyed by
            a label the deployment chooses. Each value is one
            `ccf.policy-constraint` document — an open mapping here, validated
            against :class:`PolicyConstraint` when the section is derived, the
            same discipline `operators` follows. A mapping and not a list
            (`D-IMPL-253` Q3): one manifest entry per key is what gives each
            constraint its own identity, version lane and effectivity, which a
            list under one key would collapse.
        policy: Adopter-owned and uninterpreted (`D-IMPL-136` §14.3), exactly
            as `request_contract` is. A body whose adopter content includes a
            key literally named `role` — design spec §6.2's override
            collision — parses here without complaint; resolving the
            collision is `16-29`'s concern, not this contract's.
        default_perspective: The `ccf.perspective` section body, for an
            in-process deployment with no door to derive a grant from
            (design spec §8.1).
        producers: `D-IMPL-340` — remote producer registrations, keyed by a
            label the deployment chooses. Each value is one
            `ccf.mcp-producer` body, validated against
            :class:`McpProducerRegistration` when the section is derived, on
            the `policy_constraints` discipline: a mapping, one manifest entry
            per key, so each producer has its own identity and version lane.
            Absent by default; a deployment that asks no remote producer
            derives exactly what it derived before the section existed.
        replay: The `ccf.replay-binding` section body — this deployment's
            replay binding (`R-12`, `D-IMPL-282`). Absent by default, and an
            absent section is a deployment that declares no binding rather
            than one the SDK guesses at: a resolver reaching neither an
            explicit argument nor a declaration refuses to be built.
    """

    tenant_id: str | None = None
    backend: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    backend_secrets: tuple[SecretReference, ...] = ()
    survivor_cap: int | None = None
    resolution_spec_key: str | None = None
    policy_bundle_key: str | None = None

    product_class: Mapping[str, Any]
    operators: Mapping[str, Mapping[str, Any]] | None = None
    request_contract: Mapping[str, Any] | None = None
    resolution: Mapping[str, Any] | None = None
    half_life: Mapping[str, Any] | None = None
    debt_profile: Mapping[str, Any] | None = None
    policy: Mapping[str, Any] | None = None
    policy_constraints: Mapping[str, Mapping[str, Any]] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    default_perspective: Mapping[str, Any] | None = None
    # CINV-06 / `D-IMPL-243`: ``True``, and it is load-bearing rather than
    # stylistic for `policy_constraints`' own reason — a rendered
    # ``replay: null`` would move the content address of every
    # `DeploymentConfig` already written, and pin identity IS content identity
    # (`src/ccf/deployment/pins.py::ArtifactPin`). Measured by
    # `tests/contracts/test_hash_transparency.py
    # ::test_a_config_naming_no_replay_binding_hashes_as_it_did`, not assumed.
    replay: Mapping[str, Any] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    producers: Mapping[str, Mapping[str, Any]] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # `D-IMPL-343`: the three sections the paved road reads. Hash-transparent
    # at ``None`` on the `replay` precedent above, for the same reason and
    # measured by the same test module — a config naming none of them hashes
    # as it did, so no committed pin moves.
    #
    # ``ttl`` — the `ccf.ttl-binding` section body: the class ceiling and the
    # product lifetime, declared ONCE (`D-IMPL-292`: no argument for a declared
    # value). ``door`` — the `ccf.egress-door` section body: the identity the
    # standard door asserts and the prose its tool advertises; never a URL,
    # never a credential, never a principal (those have their own homes).
    # ``agent`` — the composing agent, a `ccf.agent-definition` document
    # written where the deployment's other declarations are (CLAUDE.md §6.4:
    # an agent is data, not code). It is author-versioned, so it is derived
    # through the VERSIONED reserved path and never injected with a `semver`
    # (`D-IMPL-343` R-2; `D-IMPL-85`).
    ttl: Mapping[str, Any] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    door: Mapping[str, Any] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    agent: Mapping[str, Any] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    # `D-IMPL-343` R-7 (the consumer half): ``skills`` — one
    # `ccf.skill-catalog-entry` body per label, the deployment's statement
    # that a declared producer is asked for one required class. Author-
    # versioned, so derived through the VERSIONED reserved path like `agent`;
    # completed from the keys it depends on (`requires`, `producers`) and
    # held equal wherever it restates one. Hash-transparent at ``None`` on the
    # `replay` precedent: a config declaring no skills hashes as it did.
    skills: Mapping[str, Mapping[str, Any]] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="before")
    @classmethod
    def _no_unrecognised_sections(cls, data: object) -> object:
        """Refuse every unreserved top-level key, named, together, at once.

        `extra="forbid"` (inherited via `CCFContract`) already refuses an
        unreserved key, but its own message is Pydantic's generic *"Extra
        inputs are not permitted"* — precisely the *"refusal about a missing
        key three layers down"* `D-IMPL-136` exists to delete. This collects
        **every** offending key in one document and raises one message naming
        all of them plus every name the SDK does recognise, so `resolutoin`
        (the worked typo in design spec §4.1) is refused as *"I don't
        recognise this section"* rather than as a validation internals leak.

        `mode="before"`, not `mode="after"`: `extra="forbid"` fires during
        field validation, so an `after` validator never runs on the document
        this one exists to catch.

        The reserved-name list is read from `cls.model_fields` rather than
        restated, so the set this refusal checks against and the set
        `model_fields` actually declares cannot drift apart.
        """
        if not isinstance(data, Mapping):
            return data
        reserved = set(cls.model_fields)
        unknown = sorted(set(data) - reserved)
        if unknown:
            offending = ", ".join(repr(key) for key in unknown)
            recognised = ", ".join(sorted(reserved))
            raise ValueError(
                f"ccf_config.yaml names {offending}, which the SDK does not"
                f" recognise as a section or a deployment-level key; the"
                f" names it does recognise are: {recognised}"
            )
        return data


#: The λ_c table class (whitepaper §7.7).
HALF_LIFE_TABLE = ArtifactClass(class_id="ccf.half-life-table", contract=HalfLifeTable)
#: The decision-class debt profile class (whitepaper §7.7 CAR).
DEBT_PROFILE = ArtifactClass(class_id="ccf.debt-profile", contract=DebtProfile)
#: A deployment's replay binding (SDK-defined per CLAUDE.md §11 and §7.4;
#: ``D-IMPL-282`` ``R-12``). The third place cp-05 measured did not exist: not
#: module constants in a deployment's own Python, not an adopter-namespaced
#: artifact beside the config, but the Control Plane itself. Deployment
#: binding only — see :class:`ReplayBinding` for what that forecloses.
REPLAY_BINDING = ArtifactClass(
    class_id="ccf.replay-binding", contract=ReplayBinding
)
class ProducerOfferDeclaration(CCFContract):
    """One product class a registered producer may be asked for (`D-IMPL-340`)."""

    product_class: str
    versions_from: str

    @field_validator("versions_from")
    @classmethod
    def _floor_is_semver(cls, value: str) -> str:
        return validate_semver(value)


#: What an environment-variable NAME looks like. The two reference members of
#: :class:`McpProducerRegistration` are held to it so a literal URL, host,
#: port or token cannot be written into a Control Plane document (CINV-01).
_ENV_VAR_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class McpProducerRegistration(VersionedArtifact):
    """One remote Context Product producer a deployment is willing to ask.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §7.1, §11). Whitepaper
    §8.3 Pattern 3 makes MCP the surface a fabric exposes products on; nothing
    in it says how a *consuming* fabric declares which producers it trusts to
    answer a question. `D-IMPL-340` does: **one governed registration per
    producer, with an ``offers`` list** — Dave's ruling 4 — and *"the
    registration is the authority for expected producer identity and producer
    tenant. The answer is evidence held against that authority; it is not the
    authority itself."*

    Five declared values and one list, none with a default:

    * ``server`` — the logical name an ``mcp_product`` binding selects this
      producer by. A name, never an address.
    * ``producer_id`` — the identity every answer from this producer is held
      to (:class:`~ccf.products.door.ProducerAssertion`).
    * ``producer_tenant`` — the tenant this producer governs its products
      under; the tenant every answer's ``tenant_id`` is held to.
    * ``endpoint_from_env`` / ``credential_from_env`` — the **names** of the
      environment variables the composition root reads the endpoint URL and
      the bearer credential from. Names, so that no URL, host, port or secret
      is ever a Control Plane value; a literal is refused at parse.
    * ``offers`` — the product classes, each with a version floor, this
      deployment will ask the producer for. Not one document per class,
      by ruling.

    What this artifact does **not** carry, deliberately: a transport, a
    resource URI, a question, or any producer preference a requirement could
    read — ``requires:`` stays about the product (ruling 7).
    """

    server: str
    producer_id: str
    producer_tenant: str
    endpoint_from_env: str
    credential_from_env: str
    offers: tuple[ProducerOfferDeclaration, ...]

    @field_validator("endpoint_from_env", "credential_from_env")
    @classmethod
    def _is_an_environment_variable_name(cls, value: str) -> str:
        if _ENV_VAR_NAME.fullmatch(value) is None:
            raise ValueError(
                f"{value!r} is not an environment-variable name; a producer"
                " registration names WHERE the endpoint and credential are"
                " read from, never the values — a URL, host, port or token in"
                " a Control Plane document is exactly what CINV-01 forbids"
                " (D-IMPL-340)"
            )
        return value

    @model_validator(mode="after")
    def _offers_are_declared_once(self) -> "McpProducerRegistration":
        if not self.offers:
            raise ValueError(
                f"producer {self.server!r} offers nothing; a registration that"
                " can be asked for no class is a declaration that can never"
                " fire (D-IMPL-340)"
            )
        seen: set[str] = set()
        for offer in self.offers:
            if offer.product_class in seen:
                raise ValueError(
                    f"producer {self.server!r} offers {offer.product_class!r}"
                    " twice; one floor per class, or two lanes would compete"
                    " for one requirement (D-IMPL-340)"
                )
            seen.add(offer.product_class)
        return self


#: A remote producer registration (`D-IMPL-340`; SDK-defined per CLAUDE.md
#: §7.1). Deployment binding only: it names a producer and what it may be
#: asked for, and holds no address and no secret.
MCP_PRODUCER = ArtifactClass(
    class_id="ccf.mcp-producer", contract=McpProducerRegistration
)


class TtlBinding(VersionedArtifact):
    """One deployment's TTL figures, declared once (`D-IMPL-343`, R-3a).

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11). Whitepaper §7.6
    fixes that a product carries a TTL and that Gate 3 holds it to a class
    ceiling; it does not say where a deployment WRITES the two numbers. Before
    this class every canonical tree wrote them in a side document of its own
    and restated them as two integer keyword arguments to
    :func:`~ccf.products.resolver.build_governed_resolver` — a value stated in
    two places, which is the shape `D-IMPL-292` refuses: *no argument for a
    declared value*.

    Two declared values, neither with a default:

    * ``max_ttl_seconds`` — the class CEILING. Registering it is what mints the
      ``MAX_TTL`` pin Gate 3 resolves, which is why the class document itself
      cannot carry it.
    * ``product_ttl_seconds`` — how long a served product stays servable.
      Independent of the ceiling by construction; Gate 3 compares the two.

    **The builder's two keywords are now optional and held EQUAL to this.**
    A call that omits them reads them here; a call that states both agrees or
    is refused with both values named — never silently overridden in either
    direction. ``extra="forbid"`` is inherited, so a third key (the
    ``ttl_anchor_basis`` one canonical tree carried and nothing read) is
    refused at parse: a declared value nothing reads is documentation, not
    control.
    """

    max_ttl_seconds: int
    product_ttl_seconds: int

    @field_validator("max_ttl_seconds", "product_ttl_seconds")
    @classmethod
    def _is_a_positive_window(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(
                f"a TTL window is a positive number of seconds; got {value!r}"
                " (D-IMPL-343)"
            )
        return value


#: A deployment's TTL binding (`D-IMPL-343`; SDK-defined per CLAUDE.md §11).
TTL_BINDING = ArtifactClass(class_id="ccf.ttl-binding", contract=TtlBinding)


class EgressDoorBinding(VersionedArtifact):
    """What the standard MCP egress door asserts and advertises (`D-IMPL-343`).

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §7.1, §8.3, §11). The
    ``door:`` reserved section's document: the four values a deployment
    states about its own door, and NOTHING that belongs elsewhere.

    * ``producer_id`` — the identity the door asserts on every outcome
      (`D-IMPL-340` ruling 2). A consumer holds it to the registration IT
      governs; equality is a binding check, never an authorization.
    * ``producer_tenant`` — the tenant the assertion names. **Declared here
      and CHECKED EQUAL to the deployment's ``tenant_id`` at derivation**
      (`D-IMPL-343` R-6, Dave: *"Registration declares it; door assertion is
      held to it; the child's served tenant_id never authorizes. Do not derive
      tenant from the answer."*). A disagreement is refused by name before
      anything is registered.
    * ``tool_description`` — the prose the ``request_context_product`` tool
      advertises. A deployment value (CINV-01); the SDK writes none.
    * ``required_scope`` — the bearer scope the door requires.

    **What is refused here by construction.** ``extra="forbid"`` is
    inherited, so ``principal_id`` and ``role`` — which two shipped door
    documents restated beside ``default_perspective`` and which nothing ever
    compared — are refused as unknown keys: the door serves the deployment's
    declared perspective and has no second authority for it. No URL and no
    credential is a field either: the OAuth issuer, the resource-server
    address and the bearer credential are deployment ENVIRONMENT, read by name
    from the environment document beside the config
    (:mod:`ccf.deployment.environment`), never content-hashed into the
    Control Plane (Dave, `D-IMPL-343` GO: *"Do not put URLs or tokens in
    configuration."*).
    """

    producer_id: str
    producer_tenant: str
    tool_description: str
    required_scope: str

    @field_validator("producer_id", "producer_tenant", "tool_description", "required_scope")
    @classmethod
    def _is_stated(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "a door value is stated or absent, never blank (D-IMPL-343)"
            )
        return value


#: The standard egress door's binding (`D-IMPL-343`; SDK-defined per
#: CLAUDE.md §11). Identity and advertised prose only — no address, no
#: secret, no principal.
EGRESS_DOOR = ArtifactClass(class_id="ccf.egress-door", contract=EgressDoorBinding)


#: The parameter-level policy constraint class (whitepaper §7.8; SDK-defined
#: per CLAUDE.md §11, ``D-IMPL-253`` Q3, ledger row ``24.6-L-07``). Its own
#: class rather than a member of :data:`PRODUCT_CLASS`, so that "is this a
#: property of the product, or a rule imposed by a policy regime?" stays an
#: answerable question (``D-IMPL-251``).
POLICY_CONSTRAINT = ArtifactClass(
    class_id="ccf.policy-constraint", contract=PolicyConstraint
)
#: The L2 entity-resolution vocabulary class (whitepaper §7.3; D-IMPL-77).
#:
#: The contract lives in :mod:`ccf.assembly.worker` rather than here because the
#: spec gained ``semver`` *in place* — a wrapper holding the lane beside the spec
#: would have changed what :func:`ccf.boot.boot` receives, and that signature is
#: the one contract D-05 committed to preserving.
RESOLUTION_SPEC = ArtifactClass(
    class_id="ccf.resolution-spec", contract=EntityResolutionSpec
)
#: The Traversal category's parameter class (whitepaper §7.4).
OPERATOR_PARAMETERS_TRAVERSAL = ArtifactClass(
    class_id="ccf.operator-parameters.traversal",
    contract=TraversalNeighborhoodParametersArtifact,
)
#: The Traversal category's DIRECTED sibling (whitepaper §7.4; ledger row
#: ``24.5-L-06``). A second class id under ``ccf.operator-parameters.*`` so a
#: manifest selects the walk's direction by naming the class, never by a value.
OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS = ArtifactClass(
    class_id="ccf.operator-parameters.traversal-descendants",
    contract=TraversalDescendantsParametersArtifact,
)
#: The Temporal category's parameter class (whitepaper §7.4).
OPERATOR_PARAMETERS_TEMPORAL = ArtifactClass(
    class_id="ccf.operator-parameters.temporal",
    contract=TemporalAsOfParametersArtifact,
)
#: The Policy category's parameter class (whitepaper §7.4; D-IMPL-76 — the
#: admitted policy-bundle version set is *not* declared here; the adopter passes
#: it to the operator-registry builder).
OPERATOR_PARAMETERS_POLICY = ArtifactClass(
    class_id="ccf.operator-parameters.policy",
    contract=PolicyFilterParametersArtifact,
)
#: The Similarity category's parameter class (whitepaper §7.4). Carries the
#: construction-time corpus attribute map alongside the operator's own fields.
OPERATOR_PARAMETERS_SIMILARITY = ArtifactClass(
    class_id="ccf.operator-parameters.similarity",
    contract=SimilaritySelectParametersArtifact,
)
#: The L1 event-batch class (whitepaper §7.1). **A** ``role: load`` **class under
#: D-IMPL-80** — parsed and returned, never registered and never pinned, because
#: raw event data in the Control Plane would put an events file into replay
#: dimension 2. See :class:`SignalBatch`.
SIGNAL_BATCH = ArtifactClass(class_id="ccf.signal-batch", contract=SignalBatch)
#: The Π role-conditioning class (whitepaper §7.5).
PERSPECTIVE = ArtifactClass(class_id="ccf.perspective", contract=PerspectiveArtifact)
#: The product-class governance declaration (whitepaper §7.6). The MAX_TTL
#: *version* is deliberately absent — registering the ceiling mints it, exactly
#: as D-IMPL-76 ruled for the policy bundle's admitted-version set.
PRODUCT_CLASS = ArtifactClass(
    class_id="ccf.product-class", contract=ProductClassDeclaration
)
#: The projection's own declared operator set (SDK-defined; D-IMPL-86, design
#: E2). Distinct from :data:`PRODUCT_CLASS` on purpose: the product class carries
#: the Control Plane *claim* that fills the lineage, this carries what the
#: projection is *planned from*, and the binder compares the two. See
#: :class:`ProjectionRequirements` for why one document could not have worked.
PROJECTION_REQUIREMENTS = ArtifactClass(
    class_id="ccf.projection-requirements", contract=ProjectionRequirements
)
#: The deployment manifest class (SDK-defined; D-06, D-08, D-IMPL-80). Itself an
#: artifact, so "what did this deployment put in force" is one versioned,
#: content-hashable answer rather than a directory listing.
DEPLOYMENT_MANIFEST = ArtifactClass(
    class_id="ccf.deployment-manifest", contract=DeploymentManifest
)
#: The single-file deployment authoring document class (`D-IMPL-136`). A
#: parse-only sibling of :data:`DEPLOYMENT_MANIFEST`: this class validates
#: that a `ccf_config.yaml` says what it claims to say; deriving each section
#: into the artifact it names is `16-29`'s loader, not this class.
DEPLOYMENT_CONFIG = ArtifactClass(
    class_id="ccf.deployment-config", contract=DeploymentConfig
)


def _reject_floats(value: object, path: str) -> None:
    """Refuse a parsed YAML float anywhere in an artifact document.

    Converting one to :class:`~decimal.Decimal` here would be a silent repair of
    a value that has *already* lost precision at parse time, and would leave the
    artifact's content hash — and therefore its version identity — dependent on
    the platform's float printing. Quoting the number in the source document is
    the author's job (D-IMPL-38, D-IMPL-26).
    """
    if isinstance(value, float):
        raise ArtifactLoadError(
            f"{path or '<root>'}: float values are not admissible in a Control"
            " Plane artifact (not bit-stable across platforms); quote the value"
            " so it parses as text and is validated as a decimal"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


#: An ISO-8601 date-time that names no UTC designator and no ``±HH:MM`` offset.
#: Matched against *text*, because after :class:`_ArtifactLoader` a
#: timestamp-shaped scalar reaches this module as a string.
_NAIVE_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?$"
)


# PyYAML ships no inline types, so `SafeLoader` is `Any` here and mypy's strict
# mode refuses the subclass on principle. The base is still exactly `SafeLoader`
# at runtime — this loader narrows what it resolves and widens nothing — and
# everything it parses is validated by a typed contract immediately after, the
# same closure the `yaml` mypy override in `pyproject.toml` rests on.
class _ArtifactLoader(yaml.SafeLoader):  # type: ignore[misc]
    """A ``SafeLoader`` that reads timestamps as text and lets contracts parse them.

    ``2026-08-03T12:00:00Z`` is not an implicit timezone: ``Z`` is the ISO-8601
    UTC designator and the author stated UTC explicitly. PyYAML's timestamp
    resolver drops it and hands back a *naive* ``datetime``, which the registry
    then refuses as non-canonicalizable — punishing the author for a rule they
    did not break. That naive value is a parser defect, not an authoring one.

    So the resolver is removed here and timestamp-shaped scalars arrive as
    ``str``. A contract field annotated ``datetime`` parses the string into an
    aware value, exactly as the SDK already refuses floats rather than repairing
    them (:func:`_reject_floats`; D-IMPL-38, D-02).

    The resolver table is *copied* rather than mutated in place: mutating
    ``yaml.SafeLoader``'s class attribute would change YAML parsing for every
    other caller in the process, a far larger blast radius than this decision
    authorizes.
    """

    yaml_implicit_resolvers = {
        first_char: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:timestamp"
        ]
        for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


def _reject_naive_timestamps(value: object, path: str) -> None:
    """Refuse a date-time anywhere in an artifact document that names no zone.

    Sibling of :func:`_reject_floats`, and refused for the same reason: a
    timestamp with no UTC designator and no offset is ambiguous, and guessing a
    zone would make an artifact's meaning depend on where it was read. Say ``Z``
    or say ``+HH:MM`` (D-IMPL-38).
    """
    if isinstance(value, datetime) and value.tzinfo is None:
        raise ArtifactLoadError(
            f"{path or '<root>'}: naive timestamp; state the zone as 'Z' or an"
            " offset (D-IMPL-38)"
        )
    if isinstance(value, str) and _NAIVE_TIMESTAMP_RE.match(value):
        raise ArtifactLoadError(
            f"{path or '<root>'}: timestamp names no zone; state it as 'Z' or an"
            " offset (D-IMPL-38)"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_naive_timestamps(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_naive_timestamps(item, f"{path}[{index}]")


def parse_artifact(document: object, artifact_class: ArtifactClass) -> CCFContract:
    """Validate an already-parsed document as an instance of ``artifact_class``.

    Raises:
        ArtifactLoadError: the document contains a float or a zone-less
            timestamp, or does not satisfy the class contract.
    """
    _reject_floats(document, "")
    _reject_naive_timestamps(document, "")
    try:
        return artifact_class.contract.model_validate(document)
    except ValueError as error:
        raise ArtifactLoadError(
            f"document is not a valid {artifact_class.class_id}: {error}"
        ) from error


def load_artifact(text: str, artifact_class: ArtifactClass) -> CCFContract:
    """Parse YAML ``text`` and validate it against ``artifact_class``.

    The one supported path from a serialized Control Plane artifact to a typed
    one. Deliberately takes text rather than a path: reading the file is the
    caller's concern, and keeping I/O out of this module keeps it algorithmic.

    Parsing goes through :class:`_ArtifactLoader`, so a timestamp-shaped scalar
    reaches the contract as text and is parsed by the field's own annotation.

    Raises:
        ArtifactLoadError: the text is not YAML, holds a float or a zone-less
            timestamp, or does not satisfy the class contract.
    """
    try:
        document = yaml.load(text, Loader=_ArtifactLoader)
    except yaml.YAMLError as error:
        raise ArtifactLoadError(f"artifact is not valid YAML: {error}") from error
    return parse_artifact(document, artifact_class)
