"""``ApiDependencies`` — the named provider bundle both front doors construct.

SDK-defined (CLAUDE.md §8.3; D-IMPL-22/23). This frozen bundle is the ONE
place the HTTP API's injected fabric handles are enumerated, and it is a
*named abstraction shared by design*: the CLI's ``--local`` direct-library
mode (07-11) constructs this same type and drives the same route logic
through it, so "the CLI adds zero privileged paths" (D-IMPL-22) is a
structural fact — both fronts hold the identical handle set, and a
capability absent from this bundle exists on neither surface.

Every field is an injected Protocol or factory handle the deployment's
composition root supplies. The bundle holds no bind address, no tenant, no
threshold, and no default for anything (CINV-01): construction requires
every handle, keyword-only, and the frozen dataclass cannot grow state
after boot.

What is deliberately NOT here: any graph read or write handle. The routes
reach the fabric only through the same factories and Control Plane actions
any client uses — there is no field on this bundle that could hold a route
into L2 or L3 (INV-CH7-10; T-07-23/T-07-25).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import HITLTransportProtocol
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.mcp.egress import ProductResolverProtocol
from ccf_runtime.workflow.engine import WorkflowEngine

__ccf_mode__ = "algorithmic"

__all__ = ["ApiDependencies"]


@dataclass(frozen=True, kw_only=True)
class ApiDependencies:
    """Every injected handle the ruled noun routers need — nothing more.

    Attributes:
        control_plane: The registry agent declarations register into and
            config/workflow/status reads resolve through (the same audited
            Control Plane actions any client takes — T-07-25).
        artifact_store: The store the artifact and replay nouns read and
            write through (CLAUDE.md §7.4; D-IMPL-26).
        product_resolver: The deployment's assemble-and-gate path, exactly
            the seam the MCP egress server holds
            (:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`).
        workflow_factory: The ONLY construction path to an executable
            workflow handle (ORCH-01 — the invoke route never touches a
            raw definition).
        workflow_engine: The execution half the invoke/resume routes
            delegate to (:mod:`ccf_runtime.workflow.engine`).
        hitl_transport: The typed queue the hitl noun views and submits
            through (D-IMPL-20 — the authority path, never a notification
            channel).
        skill_catalog: Discovery over the Control Plane (D-IMPL-12).
        grant_ledger: The two-tier grant machinery the skill noun's
            mutating verb routes through (CLAUDE.md §6.2 channel 2).
    """

    control_plane: ControlPlaneRegistry
    artifact_store: ArtifactStoreProtocol
    product_resolver: ProductResolverProtocol
    workflow_factory: WorkflowFactory
    workflow_engine: WorkflowEngine
    hitl_transport: HITLTransportProtocol
    skill_catalog: SkillCatalog
    grant_ledger: GrantLedger
