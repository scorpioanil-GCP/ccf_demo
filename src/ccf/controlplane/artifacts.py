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
— policy bundles, operator parameter sets — use :class:`DeclaredArtifact`,
which fixes the envelope (class identity, lane, canonical serializability)
while leaving the declaration itself open. The SDK does not get to invent a
policy-bundle schema on a user's behalf.

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

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEBT_PROFILE",
    "HALF_LIFE_TABLE",
    "RESOLUTION_SPEC",
    "ArtifactClass",
    "ArtifactLoadError",
    "DebtProfile",
    "DeclaredArtifact",
    "HalfLifeEntry",
    "HalfLifeTable",
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

    Policy bundles, operator parameter sets, ontology declarations: the
    whitepaper fixes that these are versioned Control Plane artifacts, not what
    fields they hold. This envelope supplies the parts that are mechanism —
    class identity, semver lane, canonical serializability — and leaves
    ``declaration`` open. Anything inside it must still be canonically
    serializable, so a float in a declaration fails at registration.

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
