"""The instant a DEMONSTRATION deployment declares it serves at (`D-IMPL-378` C1).

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). Ruled by Dave as C1 (a),
2026-10-07, confirmed 2026-10-08: *"an SDK way for a deployment to declare a fixed
demonstration serve instant, honored by both transports, never usable in
production (security review required), so hw1's pinned question stops expiring
without weakening an assertion."* How "never usable in production" is enforced
is NOT ruled; the candidate this module belongs to implements the proposal's
option (b), which Dave may change — the enforcement lives in
`ccf.products.demonstration_clock`, not here.

Why a deployment needs one
--------------------------
Since `D-IMPL-358` a governed serve is judged at ``served_at``, the instant the
fabric's own clock reads when the answer is handed over: Gate 3 holds
``served_at < expires_at <= served_at + MAX_TTL``, the temporal window is
evaluated from it, and policy effectivity and composite admission are judged at
it. A demonstration pinned to a past instant — a README that quotes an address —
asks a question whose answer expired long before today's clock, and the fabric
refuses it correctly. The only honest way for such a deployment to keep working
is to SAY, in its own Control Plane, which instant it serves at.

What this module is, and is not
-------------------------------
It is the Control Plane half only, on the precedent of
`ccf.controlplane.temporal_boundary`: the typed contract, its artifact class,
the per-tenant key, and a resolution that keeps the registered version beside
the value. **It reads no clock and enforces nothing.** It never takes an instant
from a request, a caller or the environment: the only way an instant reaches a
fabric is this artifact, registered at composition from the deployment's own
config (`demonstration_serve_instant:` in ``ccf_config.yaml``).

Absence is the ordinary case and it means the real clock. Nothing here invents an
instant for a tenant that declared none (`D-IMPL-38`).
"""

from __future__ import annotations

#: CINV-03: nothing here calls a model and nothing here reads a clock.
__ccf_mode__ = "algorithmic"

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ccf.replay.record import PolicyBinding

__all__ = [
    "DEMONSTRATION_SERVE_INSTANT",
    "DemonstrationServeInstant",
    "DemonstrationServeInstantMisdeclared",
    "PinnedDemonstrationServeInstant",
    "demonstration_serve_instant_key",
    "resolve_demonstration_serve_instant",
]


class DemonstrationServeInstant(CCFContract):
    """The one instant a demonstration deployment serves every question at.

    A deployment value, and the SDK supplies none. Declaring it does not make a
    deployment a demonstration by itself: the composition that honors it
    (`ccf.products.demonstration_clock.compose_serve_clock`) refuses it outside
    the SDK's development substrates, and every record made under it pins this
    artifact's exact version in Decision Replay dimension 2.

    Attributes:
        serve_instant: The instant ``served_at`` reads, zone-bearing. A
            zone-less instant is refused: which zone it silently meant is the
            difference between two different answers (`D-IMPL-38`).
    """

    serve_instant: datetime

    @field_validator("serve_instant")
    @classmethod
    def _zoned(cls, value: datetime) -> datetime:
        """Refuse a zone-less instant rather than assume UTC (`D-IMPL-38`)."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"serve_instant {value.isoformat()!r} carries no UTC offset; a"
                " demonstration serve instant is an instant, and the SDK assumes"
                " no zone (D-IMPL-38)"
            )
        return value


#: The artifact class a deployment registers its demonstration serve instant
#: under. ``ccf.<kebab-case>`` like every SDK class id, and named for what it is
#: so that a dimension-2 binding reads as a demonstration to anyone who sees it.
DEMONSTRATION_SERVE_INSTANT: Final = ArtifactClass(
    class_id="ccf.demonstration-serve-instant", contract=DemonstrationServeInstant
)


def demonstration_serve_instant_key(*, tenant_id: str) -> str:
    """The Control Plane key one tenant's declaration registers under.

    Tenant-first (``{tenant}/{class}``), on
    `ccf.controlplane.temporal_boundary.temporal_boundary_policy_key`'s
    precedent: the registry's tenant comparison reads the segment before the
    first ``/`` (`D-IMPL-353` §1.3), and a derived key keeps two tenants off one
    declaration.
    """
    return f"{tenant_id}/{DEMONSTRATION_SERVE_INSTANT.class_id}"


class DemonstrationServeInstantMisdeclared(TypeError):
    """Something is registered at the declaration's key and it is not one.

    A configuration error, raised rather than read as an absence: absence means
    the real clock, and reporting a wrong artifact as absent would silently
    serve on the real clock a deployment that believed it had declared one.
    """


@dataclass(frozen=True)
class PinnedDemonstrationServeInstant:
    """A resolved declaration with its version identity intact.

    Held together for the reason `ccf.controlplane.temporal_boundary.
    PinnedTemporalBoundary` gives: a binding a replay needs is never
    reconstructed from whatever is registered later.

    Attributes:
        key: The canonical Control Plane key the declaration was resolved from.
        version: The exact version the registry returned.
        declaration: The typed declaration.
    """

    key: str
    version: str
    declaration: DemonstrationServeInstant

    @property
    def instant(self) -> datetime:
        """The declared serve instant."""
        return self.declaration.serve_instant

    @property
    def binding(self) -> PolicyBinding:
        """The `PolicyBinding` every record made under this declaration carries.

        Deferred import, for `PinnedTemporalBoundary.binding`'s stated reason:
        `ccf.replay.record` reaches back into `ccf.controlplane`.
        """
        from ccf.replay.record import PolicyBinding

        return PolicyBinding(key=self.key, version=self.version)


def resolve_demonstration_serve_instant(
    *, registry: ControlPlaneProtocol, tenant_id: str
) -> PinnedDemonstrationServeInstant | None:
    """Resolve one tenant's declaration, keeping its version, or ``None``.

    The tenant arrives from composition, never from a request (`D-IMPL-358`
    ruling 3). ``None`` — nothing registered at the key — means the tenant
    declared no demonstration instant, which is the ordinary case: the fabric
    serves on its own clock.

    Raises:
        DemonstrationServeInstantMisdeclared: something is registered at the key
            and it is not a `DemonstrationServeInstant`.
        Exception: anything else the registry raises propagates untouched; only
            `ControlPlaneMissing` means absence.
    """
    key = demonstration_serve_instant_key(tenant_id=tenant_id)
    try:
        version, artifact = registry.resolve_latest(key)
    except ControlPlaneMissing:
        return None
    if not isinstance(artifact, DemonstrationServeInstant):
        found = type(artifact)
        raise DemonstrationServeInstantMisdeclared(
            f"the artifact registered at {key!r} is a"
            f" {found.__module__}.{found.__qualname__}, not a"
            f" {DemonstrationServeInstant.__module__}.{DemonstrationServeInstant.__qualname__};"
            " this is a declaration error, not an absent declaration"
        )
    return PinnedDemonstrationServeInstant(key=key, version=version, declaration=artifact)
