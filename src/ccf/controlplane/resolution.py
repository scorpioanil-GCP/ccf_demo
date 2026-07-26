"""Pinned reference resolution — one implementation, two call sites.

DESIGN.md §3.5; D-IMPL-26. Every Control Plane consumer that follows a
versioned ``ccf-artifact://`` reference — the Agent & Task Factory
(:mod:`ccf.agents.factory`) and the grant ledger's policy-regime lookup
(:mod:`ccf.skills.grants`) — resolves it the same way, and must, because the
rule being applied is a governance rule rather than a convenience: a pinned
reference names *exactly one* content, probing for it is not the same as
reading it, and the read that happens is the read that is audited.

This module holds that rule once (IN-01). It had been implemented twice,
near-verbatim, differing only in what each call site wanted done about a
miss; the two copies would have drifted, and the WR-08 discipline they both
encode is precisely the kind of thing that must not drift. The helper is
therefore total on the miss case — it returns ``None`` — and each call site
wraps that in whatever its own contract requires: the factory raises, the
ledger returns a governance refusal.

The module is mechanism only (CLAUDE.md §11): it holds no key vocabulary, no
artifact class, and no domain value. The ``{tenant}/{class}/{name}`` key
shape it derives is the Control Plane's own naming convention, carried in
from the URI the caller supplies.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.artifacts.protocol import parse_artifact_uri
from ccf.controlplane.registry import (
    AmbiguousPinnedVersionError,
    ControlPlaneMissing,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ControlPlaneResolution", "resolve_pinned"]


@runtime_checkable
class ControlPlaneResolution(Protocol):
    """The read surface a pinned reference is resolved through.

    A Protocol so a remote or externally-governed Control Plane substitutes
    without its consumers knowing (CLAUDE.md §13 — Protocols over
    inheritance); :class:`~ccf.controlplane.registry.ControlPlaneRegistry` is
    the reference conformer. Deliberately read-only and exact-version: a
    consumer of this surface never registers anything and never resolves
    "latest".
    """

    def resolve(self, key: str, version: str) -> object:
        """Return the exact artifact registered as ``(key, version)``."""
        ...

    def versions(self, key: str) -> tuple[str, ...]:
        """Return every version registered under ``key``, oldest first."""
        ...

    def peek(self, key: str, version: str) -> object:
        """Return the artifact at ``(key, version)`` without auditing."""
        ...

    def artifact_class_of(self, key: str) -> str | None:
        """Return the artifact class bound to ``key``, if it was typed."""
        ...


def resolve_pinned(
    control_plane: ControlPlaneResolution, uri: str
) -> object | None:
    """Resolve one pinned ``ccf-artifact://`` reference, or return ``None``.

    The URI's naming triple maps onto the Control Plane key
    ``{tenant}/{artifact_class}/{name}``; the URI's version is the author's
    declared version (``artifact_version`` or ``semver``), matched against the
    declared version of each registered content version under that key.
    Content hashes are also accepted as URI versions, since a content address
    is the D-IMPL-26 canonical identity — that match is the fast path and
    needs no scan.

    Declared-version matching scans *every* registered content through the
    unaudited :meth:`ControlPlaneResolution.peek`, because a probe is not a
    resolution and auditing probes would record reads that never happened
    (WR-08). Exactly one :meth:`ControlPlaneResolution.resolve` call fires,
    on the content actually returned.

    Args:
        control_plane: The injected read surface.
        uri: A pinned ``ccf-artifact://`` reference.

    Returns:
        The resolved artifact, or ``None`` when the key exists but nothing
        under it declares the pinned version. The miss is returned rather
        than raised so each call site can apply its own contract — the
        factory treats it as a definition error, the grant ledger as a
        governance refusal.

    Raises:
        AmbiguousPinnedVersionError: two different contents under the key
            declare the same version the URI pins (WR-08) — a pinned
            reference must name exactly one content.
        ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
            ``@latest`` (defense in depth; the schema refuses it first).
    """
    name = parse_artifact_uri(uri)
    key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
    versions = control_plane.versions(key)
    if name.artifact_version in versions:
        return control_plane.resolve(key, name.artifact_version)
    matches: list[str] = []
    for version in versions:
        try:
            artifact = control_plane.peek(key, version)
        except ControlPlaneMissing:  # pragma: no cover - versions listed
            continue
        declared = getattr(artifact, "artifact_version", None) or getattr(
            artifact, "semver", None
        )
        if declared == name.artifact_version:
            matches.append(version)
    if len(matches) > 1:
        raise AmbiguousPinnedVersionError(key, name.artifact_version, matches)
    if matches:
        return control_plane.resolve(key, matches[0])
    return None
