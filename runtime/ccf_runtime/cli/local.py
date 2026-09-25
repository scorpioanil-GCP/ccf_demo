"""``--local`` — the same ``ApiDependencies`` bundle, no infra (D-IMPL-22).

SDK-defined (CLAUDE.md §8.3). The direct-library dev mode is not a second
code path: it constructs the exact
:class:`~ccf_runtime.http_api.dependencies.ApiDependencies` type
``create_app`` consumes — the named shared abstraction (T-07-27) — from
existing reference implementations only, and the CLI then drives the same
routes through an in-process ASGI transport. No handle exists here that a
remote HTTP client could not reach; a capability absent from the bundle
exists on neither surface.

What the empty local fabric honestly is: an in-process Control Plane
registry (the v0 reference), a file-backed dev artifact store under the
operator-chosen root, the in-memory HITL transport reference, and the
governed grant/workflow machinery over them. Seams the deployment must
wire — node bindings, the tier-2 approval sink, the product egress
resolver — are present as their honest empty forms: invoking them raises
or refuses rather than fabricating an answer (D-IMPL-38: no silent
defaults).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import Execute, Resume
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalSinkAdapter
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.serve import ServedProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import WORKFLOW_TRACE_ARTIFACT_CLASS, WorkflowEngine

__ccf_mode__ = "algorithmic"

__all__ = ["build_local_dependencies"]


def _utc_now() -> datetime:
    """The composition root's clock choice — injected everywhere below."""
    return datetime.now(UTC)


class _UnwiredNodeBinding:
    """Node execution seams the local dev fabric leaves honestly unwired.

    Conforms structurally to both
    :class:`~ccf_runtime.workflow.engine.SkillNodeBinding` and
    :class:`~ccf_runtime.workflow.engine.AgentNodeBinding`. Invocation
    raises, and the engine routes the node's exception path — a first-class
    transition (CLAUDE.md §8.1) — rather than this helper fabricating a
    result no deployment declared.
    """

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        raise RuntimeError(
            f"no skill node binding is wired in --local; step {step_name!r}"
            " needs a deployment composition root"
        )

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        raise RuntimeError(
            f"no agent node binding is wired in --local; step {step_name!r}"
            " needs a deployment composition root"
        )


def _no_products_resolver(
    *,
    tenant: str,
    product_class: str,
    version: str,
    perspective: Perspective,
    request: ProductRequest | None,
) -> ServedProduct | RefusalEnvelope:
    """The egress seam with nothing assembled — every request is a miss.

    Carries the widened ``D-IMPL-108`` signature — the authorized
    :class:`~ccf.projection.plan.Perspective` and the caller's typed request —
    and honours it in the only way an empty fabric can: by refusing. The
    arguments are named rather than swallowed by ``**_`` so that this honest
    empty form still *conforms* to
    :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`, and so that a
    deployment reading it as the template it is sees the two values its own
    resolver is obliged to condition on.
    """
    raise ProductNotServable(
        f"no gate-admitted product at {tenant}/{product_class}/{version};"
        " the --local dev fabric assembles nothing"
    )


def build_local_dependencies(*, root: Path) -> ApiDependencies:
    """Assemble the shared bundle from reference implementations only.

    Args:
        root: Operator-chosen directory for the file-backed dev artifact
            store (``--local-root``; required, never defaulted — CINV-01).

    Returns:
        The same :class:`ApiDependencies` type ``create_app`` consumes.
    """
    registry = ControlPlaneRegistry(clock=_utc_now)
    catalog = SkillCatalog(registry)
    unwired = _UnwiredNodeBinding()
    # What THIS deployment's own mechanism writes (D-IMPL-353 §1.2): the
    # workflow engine's trace, under the kinds that authorize a run. The local
    # fabric composes no resolver and no refusal recorder, so it declares no
    # replay class — declaring one it does not write would open a lane nothing
    # here holds a ReplayMint for. Everything undeclared is the client lane.
    # This composition root performs no Control Plane registration of its own
    # (the registry starts empty by design — D-IMPL-38), so it mints no
    # `Register`; a registration added here goes through the D-IMPL-354
    # recipe, never a bare key.
    store = FileArtifactStore(
        root=root / "artifacts",
        write_kinds=WriteKinds.declare({WORKFLOW_TRACE_ARTIFACT_CLASS: (Execute, Resume)}),
    )
    hitl = InMemoryHitlTransport()
    return ApiDependencies(
        control_plane=registry,
        artifact_store=store,
        product_resolver=_no_products_resolver,
        workflow_factory=WorkflowFactory(control_plane=registry),
        workflow_engine=WorkflowEngine(
            control_plane=registry,
            artifact_store=store,
            hitl_transport=hitl,
            skill_binding=unwired,
            agent_binding=unwired,
            clock=_utc_now,
        ),
        hitl_transport=hitl,
        skill_catalog=catalog,
        grant_ledger=GrantLedger(
            control_plane=registry,
            catalog=catalog,
            sink=ApprovalSinkAdapter(),
            clock=_utc_now,
        ),
    )
