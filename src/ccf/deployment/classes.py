"""Class-id → :class:`~ccf.controlplane.artifacts.ArtifactClass` resolution.

SDK-defined mechanism (CLAUDE.md §6.4 and §10), not whitepaper-derived. The
whitepaper fixes that Control Plane artifacts are typed and versioned; it says
nothing about how a *deployment manifest* names one. A manifest declares each
artifact by ``path, key, class``, where ``class`` is a string — so something has
to turn that string into the contract that validates the document.

:mod:`ccf.controlplane.artifacts` deliberately has no registry: its
:class:`~ccf.controlplane.artifacts.ArtifactClass` values are module-level
constants that callers import by name. That is the right shape for callers who
know statically which class they want, and the wrong shape for a manifest, whose
whole point is that it does not. This module supplies the missing direction, and
nothing else.

Two paths, and the split is the D-01 line
-----------------------------------------

* A class-id the SDK **owns** resolves to the SDK's own constant, from
  :data:`SDK_ARTIFACT_CLASSES` — a hand-maintained mapping, reviewed with the
  code (the shape of ``tools/lints/__main__.py::CHECKERS``). It is written out by
  name rather than scanned out of ``globals()`` so that a new SDK artifact class
  becomes a deliberate two-line addition rather than something that appears by
  import accident. ``tests/deployment/test_class_lookup.py`` holds the mapping to
  the module's actual exports, so it cannot fall behind.
* A class-id the SDK **does not own** resolves through
  :func:`~ccf.controlplane.artifacts.declared_artifact_class` to the
  :class:`~ccf.controlplane.artifacts.DeclaredArtifact` envelope. This is not a
  fallback for failure — it is the design. The SDK owns the schema of what it
  ships and never invents one for what it does not, so an unrecognized class-id
  *is* a deployment-authored schema and gets the open envelope, which fixes class
  identity, semver lane, and canonical serializability while leaving the
  declaration itself to its author.

Ordering matters for the same reason: SDK ids resolve from the reviewed constant
**first**, so a manifest cannot shadow an SDK class by naming it and receiving
the permissive envelope instead of the real contract.

The module holds no key name, no path, and no domain value — it maps SDK-owned
identifiers to SDK-owned contracts (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    RESOLUTION_SPEC,
    ArtifactClass,
    declared_artifact_class,
)

__ccf_mode__ = "algorithmic"

__all__ = ["SDK_ARTIFACT_CLASSES", "resolve_artifact_class"]

#: Every artifact class whose schema the SDK owns, keyed by ``class_id``.
#:
#: Hand-maintained on purpose, and held to :mod:`ccf.controlplane.artifacts` by
#: ``tests/deployment/test_class_lookup.py``: adding an ``ArtifactClass``
#: constant there without adding it here is a test failure, because a class the
#: SDK ships that a manifest cannot address is a class no adopter can register.
SDK_ARTIFACT_CLASSES: dict[str, ArtifactClass] = {
    HALF_LIFE_TABLE.class_id: HALF_LIFE_TABLE,
    DEBT_PROFILE.class_id: DEBT_PROFILE,
    RESOLUTION_SPEC.class_id: RESOLUTION_SPEC,
}


def resolve_artifact_class(class_id: str) -> ArtifactClass:
    """Return the :class:`ArtifactClass` a manifest's ``class`` string names.

    SDK-owned ids resolve to the SDK's own constant; every other id resolves to
    the :class:`~ccf.controlplane.artifacts.DeclaredArtifact` envelope. An
    unknown id is therefore *not* an error — it is a deployment-authored schema,
    and refusing it would be the SDK claiming ownership of a namespace that is
    not its own.

    Raises:
        ValueError: ``class_id`` is empty or whitespace-only. Refused rather
            than defaulted: an unnamed class is a manifest the audit plane
            cannot read back, and only the manifest's author knows what it
            should have said.
    """
    if not class_id.strip():
        raise ValueError(
            "refusing an empty artifact class id: an unnamed class leaves the"
            " audit plane unable to say what was registered; name it in the"
            " manifest"
        )
    sdk_class = SDK_ARTIFACT_CLASSES.get(class_id)
    if sdk_class is not None:
        return sdk_class
    return declared_artifact_class(class_id)
