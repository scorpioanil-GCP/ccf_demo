# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The standard review door: a held review item is released only on the authorized, target-bound path.

**SDK-defined** (CLAUDE.md §8.2, §8.3; round 5, item 3). Dave, 2026-10-11 20:19
MST: *"Review release must use the authorized, target-bound approval path."*

Why this exists
---------------
Since ``D-IMPL-353`` :meth:`~ccf.hitl.review_queue.ReviewQueue.release` takes
an ``Authorized[HitlSubmit]`` minted for exactly the event it releases, and the
only producer of that capability is a door's gate:
:class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer` mints it after the
deployment's authorizer allows the ``hitl.action.submit`` action on THAT event
key, for a verified credential (§1.1, §1.2). The authenticated door already
exists — :func:`~ccf_runtime.mcp.hitl_server.build_hitl_server` — but it
requires an authorizer decided over a registered, version-pinned scope mapping,
which a deployment can neither register nor declare (``CapabilityBypassError``;
``ccf.scope-mapping`` is not manifest-addressable). So a deployment holding a
:class:`~ccf.hitl.review_queue.ReviewQueue` had no supported way to let a human
release an item (cp-15 ``UBO-G12``/``UBO-G13``).

What this composes, and nothing else
------------------------------------
:func:`open_review_door` is a composition root (``D-IMPL-354``), on the terms of
:mod:`ccf_runtime.mcp.product_door`. Over its OWN Control Plane it registers ONE
scope mapping, under a composition event and a ``Register`` minted for exactly
that key, granting each deployment-stated scope the queue read and the action
submit for the deployment's tenant on exactly the event-key patterns the
deployment states for it; the door's authorizer is pinned at the version that
registration returns (``SEC-002``). It then builds the standard HITL door over
two seams onto the deployment's queue:

* the queue view — :meth:`ReviewQueue.items` for the capability's tenant;
* the action route — :meth:`ReviewQueue.release` for ``approve`` and
  :meth:`ReviewQueue.reject` for ``reject``, handed the capability the gate
  minted and the binding the door minted. The queue verifies the capability
  against the submission's event key before it reads anything, holds the
  binding to the item's submission-time content hash (TOCTOU), and audits
  every outcome; the transport refuses a binding whose subject is not the
  capability's principal.

So a release is bound three ways to its target: the authorizer allowed THIS
event key for THIS credential's scope; the capability names THIS event key;
the binding echoes THIS item's content hash. The door decides none of it — the
authorizer, the gate, the queue and the transport do.

The deployment states, as data: its tenant, its identity provider (the token
verifier, whose grants carry the authentication claims a binding is minted
from), which scope may act on which review items, and the clock an action time
is stamped from. This module holds none of them (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.authz.actions import ACTION_HITL_ACTION_SUBMIT, ACTION_HITL_QUEUE_READ
from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    Authorized,
    CompositionRegister,
    HitlQueueRead,
    HitlSubmit,
    mint_at_composition,
)
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.review_queue import ReviewQueue
from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.mcp.hitl_server import build_hitl_server

__all__ = ["ReviewActionRefused", "ReviewDoor", "open_review_door"]

#: The semver lane of the scope mapping this door registers. The mapping is the
#: door's own composition artifact, not a deployment document, so its lane is
#: the mechanism's.
_MAPPING_SEMVER = "1.0.0"

#: The two verdicts a review action carries, and the queue verb each routes to.
_APPROVE = "approve"
_REJECT = "reject"


class ReviewActionRefused(ValueError):
    """A review action named a verdict the review queue has no verb for.

    SDK-defined (CLAUDE.md §8.2). Raised before the queue is touched, so
    nothing is claimed, recorded or audited for it.
    """


@dataclass(frozen=True)
class ReviewDoor:
    """One opened review door: the composition, held; the transport, chosen by the caller.

    Attributes:
        queue: The deployment's review queue this door releases from.
        tenant_id: The tenant whose queue it serves.
        control_plane: The door's own Control Plane — the scope mapping and
            every authorization decision's audit event live here.
        scope_mapping_version: The version the authorizer is pinned to.
    """

    queue: ReviewQueue
    tenant_id: str
    control_plane: ControlPlaneRegistry
    scope_mapping_version: str
    required_scopes: tuple[str, ...]
    _token_verifier: TokenVerifier
    _authorizer: ControlPlaneTenantAuthorizer
    _clock: Callable[[], datetime]

    def server(self, *, issuer_url: str, resource_server_url: str) -> FastMCP:
        """The configured, UNSTARTED ``FastMCP`` — the standard HITL door over this queue.

        ``required_scopes`` is left empty at the HTTP layer: which scope may do
        what is the pinned scope mapping's decision, made per action and per
        event key by the authorizer, so a credential carrying one reviewer
        scope is not refused at the transport for lacking another's.
        """
        queue = self.queue

        def queue_view(authorized: Authorized[HitlQueueRead]) -> tuple[PendingHitlEvent, ...]:
            return tuple(pending for pending, _item in queue.items(tenant=authorized.tenant))

        def action_route(
            authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission
        ) -> str:
            if submission.action == _APPROVE:
                resolve = queue.release
            elif submission.action == _REJECT:
                resolve = queue.reject
            else:
                raise ReviewActionRefused(
                    f"a review action is {_APPROVE!r} or {_REJECT!r}; {submission.action!r}"
                    " names no verb the review queue has, and nothing was claimed"
                )
            outcome = resolve(
                authorized,
                event_key=submission.event_key,
                principal=submission.principal,
                annotation=submission.annotation,
                attestation=submission.attestation,
            )
            return canonical_bytes(outcome).decode("utf-8")

        return build_hitl_server(
            server_name=self.tenant_id,
            queue_view=queue_view,
            action_route=action_route,
            token_verifier=self._token_verifier,
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl(issuer_url),
                resource_server_url=AnyHttpUrl(resource_server_url),
                required_scopes=[],
            ),
            authorizer=self._authorizer,
            clock=self._clock,
        )


def _scope_mapping_key(tenant_id: str) -> str:
    """``{tenant}/{class}`` — the grammar the registry reads the tenant from (D-IMPL-353 §1.3)."""
    return f"{tenant_id}/{SCOPE_MAPPING.class_id}"


def open_review_door(
    queue: ReviewQueue,
    *,
    tenant_id: str,
    token_verifier: TokenVerifier,
    reviewer_scopes: Mapping[str, Sequence[str]],
    clock: Callable[[], datetime],
) -> ReviewDoor:
    """Compose the standard HITL door over ``queue``; choose the transport afterwards.

    Args:
        queue: The deployment's review queue.
        tenant_id: The tenant whose queue this door serves.
        token_verifier: The deployment's identity provider. A credential it
            recognizes names the human (``client_id``), the scopes, the tenants
            and the authentication claims a binding is minted from; a
            credential carrying no claims is refused at the action tool.
        reviewer_scopes: Scope → the review event-key patterns that scope may
            release or reject (``D-01`` grammar: exact, or one trailing ``*``).
            Every scope here may also read the tenant's queue.
        clock: Stamps each action's time. Required: an approval's time is the
            deployment's statement.

    Raises:
        ValueError: no scope is stated, a scope states no pattern, or a
            pattern is outside the ``D-01`` grammar.
    """
    if not reviewer_scopes:
        raise ValueError(
            "reviewer_scopes is empty: a review door through which no scope may act"
            " releases nothing; state which scope may act on which review items"
        )
    scopes: dict[str, ScopeEntry] = {}
    for scope, patterns in reviewer_scopes.items():
        if not patterns:
            raise ValueError(
                f"scope {scope!r} states no review event-key pattern; a scope that may"
                " act on nothing is not a reviewer scope"
            )
        scopes[scope] = ScopeEntry(
            tenant_patterns=(tenant_id,),
            action_ids=(ACTION_HITL_QUEUE_READ, ACTION_HITL_ACTION_SUBMIT),
            # The queue read decides on its own action id (a route resource);
            # the submit decides on the event key the caller addresses.
            resource_patterns=(ACTION_HITL_QUEUE_READ, *patterns),
        )
    control_plane = ControlPlaneRegistry()
    key = _scope_mapping_key(tenant_id)
    event = control_plane.audit_log.append(
        action="composition",
        key=key,
        version=CompositionRegister.action_id,
        resolved=True,
        occurred_at=datetime.now(UTC),
        actor=COMPOSITION_PRINCIPAL,
    )
    version = control_plane.register_typed(
        mint_at_composition(
            CompositionRegister,
            tenant=tenant_id,
            principal=COMPOSITION_PRINCIPAL,
            resource=key,
            decision_id=content_hash(event),
        ),
        ScopeMappingArtifact(semver=_MAPPING_SEMVER, scopes=scopes),
        SCOPE_MAPPING,
    )
    return ReviewDoor(
        queue=queue,
        tenant_id=tenant_id,
        control_plane=control_plane,
        scope_mapping_version=version,
        required_scopes=tuple(scopes),
        _token_verifier=token_verifier,
        _authorizer=ControlPlaneTenantAuthorizer(
            control_plane=control_plane,
            scope_mapping_key=key,
            scope_mapping_version=version,
            clock=lambda: datetime.now(UTC),
        ),
        _clock=clock,
    )
