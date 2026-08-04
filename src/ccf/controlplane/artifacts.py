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
from decimal import Decimal
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from ccf.assembly.worker import EntityResolutionSpec
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import (
    ArtifactClass,
    VersionedArtifact,
    validate_semver,
)
from ccf.operators.params import (
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalNeighborhoodParameters,
)
from ccf.signal.envelope import SignalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEBT_PROFILE",
    "HALF_LIFE_TABLE",
    "OPERATOR_PARAMETERS_POLICY",
    "OPERATOR_PARAMETERS_SIMILARITY",
    "OPERATOR_PARAMETERS_TEMPORAL",
    "OPERATOR_PARAMETERS_TRAVERSAL",
    "RESOLUTION_SPEC",
    "SIGNAL_BATCH",
    "ArtifactClass",
    "ArtifactLoadError",
    "DebtProfile",
    "DeclaredArtifact",
    "HalfLifeEntry",
    "HalfLifeTable",
    "OperatorParametersArtifact",
    "PolicyFilterParametersArtifact",
    "SignalBatch",
    "SimilaritySelectParametersArtifact",
    "TemporalAsOfParametersArtifact",
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


class HalfLifeEntry(CCFContract):
    """One row of a λ_c table (whitepaper §7.7; INV-CH7-59).

    The whitepaper's illustrative table is four columns wide — observation
    type, λ_c band, dominant decay driver, supersession event — and the *row
    shape is the commitment*, so all four are required. The driver and the
    supersession event are not documentation: supersession is a Policy event
    that collapses the decay curve rather than continuing it (INV-CH7-60), and
    an entry that never names its supersession event cannot participate in that
    mechanism later.

    Attributes:
        half_life_seconds: λ_c as whole seconds. Integer rather than a
            fractional quantity because seconds are exact and floats are not;
            sub-second half-lives are outside the bands the whitepaper's
            operational story contemplates.
        decay_driver: What actually makes this observation type go stale.
        supersession_event: The event that ends this observation's validity for
            current-value queries.
    """

    half_life_seconds: int
    decay_driver: str
    supersession_event: str

    @field_validator("half_life_seconds")
    @classmethod
    def _rate_is_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("half_life_seconds must be positive")
        return value


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
    """

    risk_sensitivity: Decimal
    forced_llm_threshold: Decimal
    fail_closed_threshold: Decimal

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

    It declares **one artifact-only field beyond the operator's contract**, and
    the asymmetry is deliberate rather than an oversight.

    Attributes:
        similarity_corpus_attribute_by_class: ``entity_class -> attribute key``
            naming the attribute whose text forms that class's corpus entry. It
            governs :class:`~ccf.similarity.token_overlap.TokenOverlapIndex`
            *construction* — the registry builder reads it before the operator
            exists — and it is deliberately **absent** from
            :class:`~ccf.operators.params.SimilaritySelectParameters`, because
            putting a construction-time value on the per-invocation parameter set
            would make the L4 invoke contract carry state no invocation reads.
            No default: a class absent from this mapping contributes no corpus
            entry, and guessing an attribute name is guessing what a deployment
            meant by "similar".
    """

    similarity_corpus_attribute_by_class: Mapping[str, str]


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
    permitted_classifications: frozenset[str]


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


#: The λ_c table class (whitepaper §7.7).
HALF_LIFE_TABLE = ArtifactClass(class_id="ccf.half-life-table", contract=HalfLifeTable)
#: The decision-class debt profile class (whitepaper §7.7 CAR).
DEBT_PROFILE = ArtifactClass(class_id="ccf.debt-profile", contract=DebtProfile)
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
