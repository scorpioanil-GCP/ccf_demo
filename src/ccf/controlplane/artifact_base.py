"""The versioned-artifact primitives, in a module nothing in ``ccf`` sits above.

Whitepaper §6.3 (semver on contracts), §7.8 (the Control Plane declares what
the fabric may do); DESIGN.md §7. SDK-defined placement (CLAUDE.md §6.4).

This module exists for one structural reason, and the reason is load-bearing
enough to state before anything else in it:

**It imports nothing from ``ccf`` except :mod:`ccf.contracts.base`, and that
constraint is the property it exists to hold.** Adding any other ``ccf`` import
here re-closes an import cycle that this module was created to break, and it
would do so at *import* time rather than at lint time — the package would stop
importing at all. The cycle is concrete: :mod:`ccf.controlplane.artifacts` must
name :class:`~ccf.assembly.worker.EntityResolutionSpec` to declare the
``ccf.resolution-spec`` class (D-IMPL-77 requires the spec gain ``semver`` *in
place*, so there is no wrapper to name instead); :mod:`ccf.assembly.worker`
imports :mod:`ccf.controlplane.registry`; and ``registry`` needs
:class:`ArtifactClass`. With ``ArtifactClass`` living in ``artifacts``, that is
``artifacts -> worker -> registry -> artifacts``. With it living here, ``registry``
no longer imports ``artifacts`` at all and the chain terminates.

Three things live here, and they are the three the cycle turned on:

* :func:`validate_semver` — the one home of the semver grammar (E7). Every
  versioned artifact field validates through it rather than re-declaring the
  regex, so the grammar cannot drift between modules.
* :class:`VersionedArtifact` — the shared surface of every SDK-owned artifact
  class. **Public**, unlike the module-private ``_VersionedArtifact`` it
  replaces: L2's :class:`~ccf.assembly.worker.EntityResolutionSpec` now inherits
  it, and an L2 contract inheriting a module-private Control Plane type is a
  relocation hazard the next refactor trips over.
* :class:`ArtifactClass` — the identity-plus-contract pair a registration is
  checked against.

:mod:`ccf.controlplane.artifacts` re-exports all three, so every import path
that worked before this module existed still resolves.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import field_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ArtifactClass",
    "VersionedArtifact",
    "validate_semver",
]

#: Semantic Versioning ``MAJOR.MINOR.PATCH`` with optional pre-release/build.
#: The *grammar* is mechanism (whitepaper §6.3 requires semver on contracts);
#: which version an artifact is on is the author's statement.
_SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def validate_semver(value: str) -> str:
    """Return ``value`` if it is a well-formed semantic version, else raise.

    The one place the semver grammar lives (whitepaper §6.3 requires semver on
    contracts). Every versioned artifact field — the single-lane ``semver`` of
    SDK artifact classes, and the D-IMPL-28 two-field lanes on agent and prompt
    artifacts — validates through this function rather than re-declaring the
    regex, so the grammar cannot drift between modules.

    Raises:
        ValueError: ``value`` is not a semantic version.
    """
    if not _SEMVER_RE.match(value):
        raise ValueError(f"{value!r} is not a semantic version")
    return value


class VersionedArtifact(CCFContract):
    """Shared surface of every SDK-owned artifact class: its own semver lane.

    ``semver`` has no default. An artifact whose author never stated its lane
    cannot be registered, because a default would be a version nobody chose and
    the registry's D-05 bump check would then compare content hashes against a
    lane the author never asserted. Lanes are per artifact class and never
    compared across classes (the same discipline as per-product-class schema
    lanes, INV-CH7-49).

    Public rather than module-private (this plan, D-IMPL-77): L2's
    :class:`~ccf.assembly.worker.EntityResolutionSpec` inherits it, so it is
    part of the surface an adopter reads, not an implementation detail of one
    Control Plane module.
    """

    semver: str

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)


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
