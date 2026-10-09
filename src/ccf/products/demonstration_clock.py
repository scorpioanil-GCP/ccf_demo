"""Composing a declared demonstration serve instant — and refusing it outside a demonstration.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). `D-IMPL-378` C1 (a), Dave:
*"an SDK way for a deployment to declare a fixed demonstration serve instant,
honored by both transports, never usable in production (security review
required)"*. The declaration is
`ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant`; this
module is where a composition turns it into the fabric's serve clock.

**RULED: option (b)** — Dave, 2026-10-08 10:50 MST, *"Option b on C1 and
C2-A"* (the `D-IMPL-378` dated amendment of that time). How "never usable in
production" is enforced: the declaration is refused unless the fabric runs on the
SDK's own approved development backends, and every record made under it pins it.
The options it was chosen among are lane ``378d-democlock``'s ``PROPOSAL-C1.md``
§4. **Decision 6 (b)** — Dave, 2026-10-09 (confirmed at 06:21 MST): *"Restrict
demonstration time to the SDK's own approved development backends. Explicitly
amend the broader “declares itself” wording."* Option (b) there reads *"tighten
the code to the SDK's own SQLite / in-memory classes"*; rule 4 below is that
tightening.
**C1-late, RULED (a)** — Dave, 2026-10-08 12:29 MST: *"Running services retain
their startup snapshot. Document that later registration takes effect only after
rebuilding."* Rule 2 below is that snapshot, and says what rebuilding is on each
surface.

The rules, each enforced here or by `ccf.products.resolver.GovernedResolver`
--------------------------------------------------------------------------------
1. **One source.** The instant comes only from the tenant's Control Plane
   declaration, resolved once, at composition. Nothing on a request — ``asked_at``,
   a parameter, a decision-instant parameter, an MCP tool argument — reaches it:
   a serve instant taken from caller input would let any question move the
   fabric's clock (`D-GATE-358` (3)).
2. **Pinned at composition: the startup snapshot.** :func:`compose_serve_clock`
   reads the declaration when the resolver is built and never again, so a
   declaration registered into a running fabric does not reach a built resolver,
   and a running service cannot be switched into demonstration mode. It takes
   effect only in a resolver built after it is registered: a composition root's
   next :func:`~ccf.products.resolver.build_governed_resolver` call over the same
   Control Plane; for the in-process adapter, which boots each deployment once per
   process from its ``ccf_config.yaml``, the deployment's next boot. The paved
   road builds a resolver for every question but composes its own clock, so it
   never honors a declaration: one registered after
   :func:`~ccf.products.product.open_product` is refused by name at the next
   question (:class:`DemonstrationServeInstantConflict`). Measured in
   ``tests/client/test_demonstration_serve_instant.py``:
   ``test_a_declaration_registered_after_composition_does_not_reach_the_resolver``,
   ``test_a_declaration_registered_after_composition_takes_effect_only_in_a_resolver_built_after_it``
   and ``test_the_paved_road_refuses_a_declaration_registered_after_open_at_the_next_question``.
3. **One authority.** A composition that supplies its own clock while the
   deployment declares an instant is refused by name
   (:class:`DemonstrationServeInstantConflict`) rather than letting either win.
4. **The SDK's own approved development backends only** (option (b), narrowed
   by decision 6 (b)). Refused (:class:`DemonstrationServeInstantRefused`)
   unless the graph adapter is one the SDK ships whose own registration is a
   development reference (`ccf.graph.registry.is_sdk_development_reference`:
   the SDK's SQLite and in-memory adapters) and the artifact store is an
   instance of the SDK's file-backed store class — the implementations
   CLAUDE.md §7.4 and §9 name as development references (``D-IMPL-02``). An
   adapter's declaration about itself does not count: a third-party
   registration that sets
   `ccf.graph.registry.BackendRegistration.development_reference` is refused,
   since that field is read only on the SDK's own records. The store check is
   ``isinstance``, so a subclass of the SDK's file-backed store passes it. The
   adapter is asked about through the registry, so core names none
   (``D-IMPL-93`` property (2)).
5. **Confined to the serve clock.** Only ``served_at`` moves. The Control Plane
   audit log, the erasure consult's audit stamp, the door's authentication and
   entitlement clocks keep their own; Context Debt keeps the decision instant
   (`D-IMPL-358` ruling 6).
6. **Audit by construction.** :class:`DeclaredServeClock` carries the
   declaration's exact pin, and the resolver appends it to dimension 2 of every
   record it writes while serving on this clock — served and refused alike.
7. **Never silently ignored.** A tenant whose Control Plane holds several
   versions of its declaration is refused at composition
   (`ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstantMisplaced`)
   rather than served on whichever was registered last; a declaration at the
   wrong key is refused at boot by the same class before anything is registered,
   and two manifest entries at one key are refused for every class by
   `ccf.deployment.manifest.manifest_under_tenant` (``ManifestKeysPlaceToOneKey``).

This module is algorithmic (CINV-03): no model, no clock read of its own.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.demonstration_serve_instant import (
    DemonstrationServeInstantMisplaced,
    PinnedDemonstrationServeInstant,
    demonstration_serve_instant_key,
    resolve_demonstration_serve_instant,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.erasure.approval import PinnedPolicySource
from ccf.graph.registry import is_sdk_development_reference

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ccf.artifacts.protocol import ArtifactStoreProtocol
    from ccf.deployment import BootedFabric
    from ccf.replay.record import PolicyBinding

__ccf_mode__ = "algorithmic"

__all__ = [
    "DeclaredServeClock",
    "DemonstrationServeInstantConflict",
    "DemonstrationServeInstantRefused",
    "compose_serve_clock",
]

#: Why the production guard refused, as a stable token a caller can branch on.
RefusalReason = Literal["graph-substrate-not-development", "artifact-store-not-development"]


class DemonstrationServeInstantRefused(ValueError):
    """A declared demonstration serve instant outside the SDK's own approved development backends.

    Raised at composition, before any question is answered. Ruled option
    (b) (Dave, 2026-10-08): a frozen serve clock keeps expired answers servable and judges
    policy and admission at a stale instant, so it is refused on any substrate a
    production deployment would run on. Narrowed by decision 6 (b) (Dave,
    2026-10-09) to the SDK's own approved development backends: a third-party
    graph adapter is refused whatever its registration declares.

    Attributes:
        reason: Which substrate refused it.
        key: The declaration's Control Plane key.
    """

    def __init__(self, message: str, *, reason: RefusalReason, key: str) -> None:
        super().__init__(message)
        self.reason: RefusalReason = reason
        self.key = key


class DemonstrationServeInstantConflict(ValueError):
    """A composition supplied its own clock while the deployment declares an instant.

    Two authorities for one instant, refused by name rather than letting one
    silently win (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B.2: a value stated in
    two authorities that can drift apart).

    Attributes:
        key: The declaration's Control Plane key.
    """

    def __init__(self, message: str, *, key: str) -> None:
        super().__init__(message)
        self.key = key


@dataclass(frozen=True)
class DeclaredServeClock:
    """The serve clock a declared demonstration instant composes: it returns that instant.

    It carries the declaration's pin, so whatever reads ``served_at`` from it can
    also say which declaration set it — the resolver appends :attr:`binding` to
    dimension 2 of every record it writes on this clock.

    Attributes:
        pinned: The declaration, resolved once at composition, with its version.
    """

    pinned: PinnedDemonstrationServeInstant

    def __call__(self) -> datetime:
        """The declared instant — the same value on every call."""
        return self.pinned.instant

    @property
    def binding(self) -> PolicyBinding:
        """The declaration's exact ``(key, version)`` pin."""
        return self.pinned.binding


def _refuse_outside_development_substrates(
    *, pinned: PinnedDemonstrationServeInstant, graph_adapter: str, artifact_store: object
) -> None:
    """Raise unless the graph and the artifact store are the SDK's own development backends."""
    # Decision 6 (b): asked of the registry about the adapter the fabric booted,
    # and answered from the SDK's own adapter package and the SDK's own record,
    # never from the adapter's declaration about itself, and never from a name
    # list in core (`D-IMPL-93`).
    if not is_sdk_development_reference(graph_adapter):
        raise DemonstrationServeInstantRefused(
            f"{pinned.key!r} declares a demonstration serve instant"
            f" ({pinned.instant.isoformat()}), and this fabric's graph adapter"
            f" {graph_adapter!r} is not one of the SDK's own approved development"
            " backends. An adapter's declaration about itself does not make it"
            " one: `BackendRegistration.development_reference` is read only on"
            " the SDK's own registrations. A fixed serve clock keeps expired"
            " answers servable and judges policy and admission at a stale"
            " instant, so it is refused on any substrate a production deployment"
            " runs on (D-IMPL-378 C1, decision 6 (b))",
            reason="graph-substrate-not-development",
            key=pinned.key,
        )
    if not isinstance(artifact_store, FileArtifactStore):
        raise DemonstrationServeInstantRefused(
            f"{pinned.key!r} declares a demonstration serve instant"
            f" ({pinned.instant.isoformat()}), and this composition's artifact"
            f" store is a {type(artifact_store).__name__}, not the SDK's"
            " file-backed development store. A record written on a fixed serve"
            " clock claims a serve time that was not real, so it is refused"
            " outside the development store (D-IMPL-378 C1)",
            reason="artifact-store-not-development",
            key=pinned.key,
        )


def compose_serve_clock(
    *,
    control_plane: ControlPlaneProtocol,
    fabric: BootedFabric,
    artifact_store: ArtifactStoreProtocol,
    admission_clock: Callable[[], datetime],
    sdk_clock: Callable[[], datetime],
) -> Callable[[], datetime]:
    """The serve clock this composition runs on: the declared instant, or ``admission_clock``.

    Called once, by `ccf.products.resolver.build_governed_resolver`, after its
    artifact store is selected and before anything is built over it.

    **Read once: the startup snapshot** (C1-late, ruled (a), Dave 2026-10-08).
    The declaration read here is the one the resolver serves on for its whole
    life. One registered later takes effect only when a resolver is built again
    (the module docstring, rule 2, says what that is on each surface).

    Args:
        control_plane: The composition's Control Plane. Where it offers the
            unaudited pinned-read surface (`ccf.erasure.approval.PinnedPolicySource`,
            which `build_governed_resolver` already requires) it is probed with
            ``versions`` first, so a deployment that declares nothing gains no
            audit event; a declaration that exists is resolved through the
            audited read, so the composition's consult of it is on the log.
        fabric: The booted fabric — its tenant and its graph adapter's pin.
        artifact_store: The store records will be written to, before any
            wrapping the composition adds.
        admission_clock: The clock the caller composed.
        sdk_clock: The SDK's own default clock, so "the caller composed none" is
            an identity test rather than a guess.

    Raises:
        ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstantMisplaced:
            the Control Plane holds several versions of the tenant's
            declaration, so whichever was registered last would silently win.
        DemonstrationServeInstantConflict: the caller composed its own clock and
            the deployment declares an instant.
        DemonstrationServeInstantRefused: the declaration sits on a graph
            adapter that is not one of the SDK's own approved development
            backends, whatever that adapter's registration declares, or on an
            artifact store that is not an instance of the SDK's file-backed
            store class.
    """
    key = demonstration_serve_instant_key(tenant_id=fabric.tenant_id)
    if isinstance(control_plane, PinnedPolicySource):
        versions = control_plane.versions(key)
        if not versions:
            return admission_clock
        # Several declarations: the latest would win and every other would
        # silently do nothing, so composition refuses rather than choosing.
        if len(versions) > 1:
            raise DemonstrationServeInstantMisplaced(
                f"{key!r} holds {len(versions)} versions of this tenant's"
                f" demonstration serve instant ({', '.join(versions)}); a tenant"
                " serves at one, and composing on the latest would silently"
                " ignore the rest. Register exactly one (D-IMPL-378 C1)",
                reason="several-declarations",
                keys=tuple(key for _ in versions),
                expected=key,
            )
    pinned = resolve_demonstration_serve_instant(
        registry=control_plane, tenant_id=fabric.tenant_id
    )
    if pinned is None:
        return admission_clock
    if admission_clock is not sdk_clock:
        raise DemonstrationServeInstantConflict(
            f"this composition supplies its own clock and {key!r} declares a"
            f" demonstration serve instant ({pinned.instant.isoformat()}). One"
            " serve instant has one authority: remove the composed clock, or"
            " remove the declaration (D-IMPL-378 C1)",
            key=key,
        )
    _refuse_outside_development_substrates(
        pinned=pinned, graph_adapter=fabric.handle.adapter.name, artifact_store=artifact_store
    )
    return DeclaredServeClock(pinned=pinned)
