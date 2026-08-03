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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ArtifactClass",
    "ArtifactLoadError",
    "DebtProfile",
    "DeclaredArtifact",
    "HalfLifeEntry",
    "HalfLifeTable",
    "declared_artifact_class",
    "load_artifact",
    "parse_artifact",
    "validate_semver",
]

#: Semantic Versioning ``MAJOR.MINOR.PATCH`` with optional pre-release/build.
#: The *grammar* is mechanism (whitepaper §6.3 requires semver on contracts);
#: which version an artifact is on is the author's statement.
_SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)

_UNIT = Decimal(1)
_ZERO = Decimal(0)


def validate_semver(value: str) -> str:
    """Return ``value`` if it is a well-formed semantic version, else raise.

    The one place the semver grammar lives (whitepaper §6.3 requires semver on
    contracts). Every versioned artifact field — the single-lane ``semver`` of
    SDK artifact classes here, and the D-IMPL-28 two-field lanes on agent and
    prompt artifacts — validates through this function rather than re-declaring
    the regex, so the grammar cannot drift between modules.

    Raises:
        ValueError: ``value`` is not a semantic version.
    """
    if not _SEMVER_RE.match(value):
        raise ValueError(f"{value!r} is not a semantic version")
    return value


class ArtifactLoadError(ValueError):
    """A serialized artifact cannot be admitted as written.

    Raised — never repaired — because the two failure modes it covers are both
    silent-corruption risks: a YAML float (not bit-stable across platforms, and
    refused outright by the canonical serializer) and a document that does not
    satisfy its declared class contract.
    """


@dataclass(frozen=True)
class ArtifactClass:
    """The identity and contract of one Control Plane artifact class.

    Kept as a plain frozen dataclass rather than a contract because it is
    *about* artifacts rather than being one: it carries a Python type, which
    has no canonical serialization and never belongs in a content hash.

    Attributes:
        class_id: Stable identifier recorded on audit events, so the audit
            plane answers "what class of thing was registered" without
            re-reading the artifact.
        contract: The contract every artifact of this class must satisfy.
    """

    class_id: str
    contract: type[CCFContract]

    def validate(self, artifact: object) -> CCFContract:
        """Return ``artifact`` if it satisfies this class, else raise.

        Raises:
            TypeError: the artifact is not an instance of the class contract.
                A near-miss mapping with the right keys is still a rejection —
                structural luck is not a contract.
        """
        if not isinstance(artifact, self.contract):
            raise TypeError(
                f"artifact for class {self.class_id!r} must be a"
                f" {self.contract.__name__}, got {type(artifact).__name__}"
            )
        return artifact


class _VersionedArtifact(CCFContract):
    """Shared surface of every SDK-owned artifact class: its own semver lane."""

    semver: str

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)


class DeclaredArtifact(_VersionedArtifact):
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


class HalfLifeTable(_VersionedArtifact):
    """The per-observation-type λ_c table, as a versioned artifact (INV-CH7-58).

    The table ships empty of rows by design: ``entries`` has no default, so a
    deployment that registers no calibration gets a registration failure rather
    than a fabric that decays everything at a rate the SDK picked. λ_c "is
    domain-specific" and the whitepaper's own values are "illustrative, not
    empirical" — the SDK's contribution is this shape and the curve in
    :mod:`ccf.halflife.decay`.
    """

    entries: Mapping[str, HalfLifeEntry] = Field(min_length=1)


class DebtProfile(_VersionedArtifact):
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


def parse_artifact(document: object, artifact_class: ArtifactClass) -> CCFContract:
    """Validate an already-parsed document as an instance of ``artifact_class``.

    Raises:
        ArtifactLoadError: the document contains a float, or does not satisfy
            the class contract.
    """
    _reject_floats(document, "")
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

    Raises:
        ArtifactLoadError: the text is not YAML, holds a float, or does not
            satisfy the class contract.
    """
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ArtifactLoadError(f"artifact is not valid YAML: {error}") from error
    return parse_artifact(document, artifact_class)
