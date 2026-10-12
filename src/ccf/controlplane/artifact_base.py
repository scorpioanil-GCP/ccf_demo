# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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

Two things joined them for the same reason: :class:`ArtifactClassIdMismatch`
and :class:`ReservedArtifactClassId`, the two refusals
:meth:`ArtifactClass.validate` raises, live beside the method that raises them
because ``registry`` reaches them through ``ArtifactClass`` and must not import
``artifacts`` (``D-IMPL-378``). ``ReservedArtifactClassId`` moved here from
:mod:`ccf.controlplane.artifacts` when ``validate`` began raising it (the K1
follow-up), and its reserved prefix moved with it.

:mod:`ccf.controlplane.artifacts` re-exports all five, so every import path
that worked before this module existed still resolves.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from pydantic import field_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ArtifactClass",
    "ArtifactClassIdMismatch",
    "ReservedArtifactClassId",
    "VersionedArtifact",
    "validate_semver",
]

#: The contract field in which a document STATES the artifact class it is
#: (``D-IMPL-378``). Of the contracts the SDK's artifact classes validate, only
#: the open envelope, :class:`~ccf.controlplane.artifacts.DeclaredArtifact`,
#: declares it at top level; an adopter's own artifact contract that declares it
#: states its class the same way and is held to it the same way.
_STATED_CLASS_FIELD = "class_id"

#: The prefix the SDK owns (``D-IMPL-84``), stated once for the three places
#: that apply the reservation: :meth:`ArtifactClass.validate` below,
#: :func:`ccf.controlplane.artifacts.declared_artifact_class` and
#: :func:`ccf.deployment.classes.resolve_artifact_class`, which import it.
#: Private, and deliberately not in ``__all__``: the reservation is a behavior
#: of those three, and an exported string would invite an adopter to branch on
#: it instead of letting the refusal fire.
_RESERVED_CLASS_ID_PREFIX: Final = "ccf."

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


class ArtifactClassIdMismatch(TypeError, ValueError):
    """A document states one artifact class and is presented as another (``D-IMPL-378``).

    SDK-defined (CLAUDE.md §6.4 and §10). A document whose contract declares a
    top-level ``class_id`` — the open envelope
    :class:`~ccf.controlplane.artifacts.DeclaredArtifact`, which every adopter
    class id resolves to — states the class it is. The :class:`ArtifactClass`
    it is parsed or registered as is the class it is *presented* as: the class a
    manifest entry names, or the class a caller registers it under. Two
    statements of one fact. Admitted while they disagree, the registry would
    bind the key to the presented class, the audit plane would record it and
    the boot would pin it into Decision Replay dimension 2, while the artifact
    resolved back says it is another class. Refused instead, by name, in
    :meth:`ArtifactClass.validate`, which
    :func:`~ccf.controlplane.artifacts.parse_artifact`,
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_typed` and
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned`
    all call before anything is registered.

    A ``TypeError`` because ``register_typed`` and ``register_versioned``
    document one for an artifact that does not satisfy its class, and a
    ``ValueError`` because a parse door's caller catches one for a document that
    does not; a caller of either keeps catching this one.

    Attributes:
        presented_class_id: The class the document was parsed or registered as.
        document_class_id: The class the document itself states.
    """

    def __init__(self, *, presented_class_id: str, document_class_id: object) -> None:
        self.presented_class_id, self.document_class_id = presented_class_id, document_class_id
        super().__init__(
            f"ArtifactClassIdMismatch: the document states class_id"
            f" {document_class_id!r} and is presented as artifact class"
            f" {presented_class_id!r}. A document names the class it is, and one"
            " filed as another would be bound, audited and pinned into Decision"
            f" Replay dimension 2 as {presented_class_id!r} while the artifact"
            f" resolved back says {document_class_id!r}, so nothing is parsed or"
            " registered. Correct the document's class_id, or present it as the"
            " class it states (D-IMPL-378)"
        )


class ReservedArtifactClassId(ValueError):
    """A class id in the SDK's reserved ``ccf.`` namespace, offered for an adopter's class.

    ``D-IMPL-84`` reserves the prefix for the SDK. The SDK's own classes are
    typed ``ArtifactClass`` constants over contracts it wrote, and none of those
    contracts states a ``class_id``; a document that states its own class — the
    open :class:`~ccf.controlplane.artifacts.DeclaredArtifact` envelope, or an
    adopter's contract that declares ``class_id`` — is therefore an adopter's
    content. Admitted under a ``ccf.`` id, it would register under an SDK class
    name, the registry would bind the key to that name, and the boot would pin
    it into Decision Replay dimension 2. Three places refuse it, by this name:

    * :func:`~ccf.controlplane.artifacts.declared_artifact_class`, before any
      class exists (``D-IMPL-378`` K1 (b), Dave, 2026-10-08 12:29 MST);
    * :meth:`ArtifactClass.validate`, for a class built directly with the
      public constructor, before anything is registered or audited
      (``D-IMPL-378`` K1 follow-up (b), Dave, 2026-10-08 16:40 MST: *"Close the
      direct-construction bypass while preserving legitimate SDK classes."*);
    * :func:`~ccf.deployment.classes.resolve_artifact_class`, the manifest
      door's resolver, for a ``ccf.`` id the SDK does not ship, before the
      envelope is reached (``D-IMPL-84``; it raised a plain ``ValueError``
      until OWED-RULINGS-3 item 3P2 (b), Dave, 2026-10-09 06:21 MST: one rule,
      one name).

    A ``ValueError``, so a caller that catches ``ValueError`` around any of
    them keeps catching it.

    **Not refused, by ruling** (``D-IMPL-378`` OWED-RULINGS-3 item 3P1 (a),
    Dave, 2026-10-09 06:21 MST: disclose and leave it): a class built directly
    under a ``ccf.`` id over a contract with no ``class_id`` field. Its
    documents state no class, so there is nothing for this refusal to read,
    and they register under the SDK's class name. It is deliberate code, and
    no document, manifest, config or envelope reaches it. Measured:
    ``tests/controlplane/test_reserved_namespace_disclosed_residual.py::test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers``.

    Attributes:
        class_id: The id that was refused.
    """

    def __init__(self, class_id: str) -> None:
        super().__init__(
            f"artifact class id {class_id!r} claims the SDK's reserved"
            f" {_RESERVED_CLASS_ID_PREFIX!r} prefix (D-IMPL-84; D-IMPL-378 K1);"
            " a document that states its own class — the open DeclaredArtifact"
            " envelope, or any contract declaring class_id — is refused under"
            " it, because it would register, pin and enter Decision Replay"
            " dimension 2 under an SDK class name with content no SDK contract"
            " validated — register an SDK class with the SDK's own"
            " ArtifactClass constant, or choose a class id in your own namespace"
        )
        self.class_id = class_id


@dataclass(frozen=True)
class ArtifactClass:
    """The identity and contract of one Control Plane artifact class.

    Kept as a plain frozen dataclass rather than a contract because it is
    *about* artifacts rather than being one: it carries a Python type, which
    has no canonical serialization and never belongs in a content hash.

    **What the reserved ``ccf.`` namespace does not stop** (``D-IMPL-378``
    OWED-RULINGS-3 item 3P1 (a), Dave, 2026-10-09 06:21 MST: disclose and
    leave it). :meth:`validate` refuses a document that states its own class
    under a ``ccf.`` id (:class:`ReservedArtifactClassId`), but a contract with
    no ``class_id`` field states nothing to refuse: code that writes such a
    contract and builds this class directly under a ``ccf.`` id registers its
    documents under the SDK's class name, the key bound to that id and the
    registration audited under it. That is deliberate code, not a document;
    the reservation holds on every document, manifest, config and envelope
    route. Measured:
    ``tests/controlplane/test_reserved_namespace_disclosed_residual.py::test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers``.

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

        Satisfying the class is three things. The artifact is an instance of
        the class contract. Where that contract declares a top-level
        ``class_id``, the class the artifact states is this one
        (``D-IMPL-378``). And such a self-stating document is never this
        class when this class's id is in the SDK's reserved ``ccf.`` namespace
        (``D-IMPL-84``; ``D-IMPL-378`` K1 follow-up): the SDK's own classes
        state no ``class_id``, so one that does is an adopter's content under
        an SDK class name. The second and third are read from the artifact's
        own type and statement, never supplied by the caller, so no way of
        building this :class:`ArtifactClass` — the manifest's resolver,
        :func:`~ccf.controlplane.artifacts.declared_artifact_class` or a
        direct construction — reaches a document that says it is something
        else, or files a self-stating document under an SDK class name.

        Raises:
            TypeError: the artifact is not an instance of the class contract.
                A near-miss mapping with the right keys is still a rejection —
                structural luck is not a contract.
            ArtifactClassIdMismatch: the artifact states a ``class_id`` other
                than this class's own.
            ReservedArtifactClassId: the artifact states this class's own
                ``class_id`` and that id starts with the reserved ``ccf.``
                prefix.
        """
        if not isinstance(artifact, self.contract):
            raise TypeError(
                f"artifact for class {self.class_id!r} must be a"
                f" {self.contract.__name__}, got {type(artifact).__name__}"
            )
        if _STATED_CLASS_FIELD in type(artifact).model_fields:
            stated = getattr(artifact, _STATED_CLASS_FIELD)
            if stated != self.class_id:
                raise ArtifactClassIdMismatch(
                    presented_class_id=self.class_id, document_class_id=stated
                )
            # The base `str` method, never the id's own: a `str` subclass built
            # in code compares equal to the plain id and could answer for itself.
            if str.startswith(self.class_id, _RESERVED_CLASS_ID_PREFIX):
                raise ReservedArtifactClassId(self.class_id)
        return artifact
