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
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalSinkAdapter
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.products.gates import ServableProduct
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import WorkflowEngine

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
    *, tenant: str, product_class: str, version: str
) -> ServableProduct:
    """The egress seam with nothing assembled — every request is a miss."""
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
    store = FileArtifactStore(root=root / "artifacts")
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
