"""``ApiDependencies`` — the named provider bundle both front doors construct.

SDK-defined (CLAUDE.md §8.3; D-IMPL-22/23). This frozen bundle is the ONE
place the HTTP API's injected fabric handles are enumerated, and it is a
*named abstraction shared by design*: the CLI's ``--local`` direct-library
mode (07-11) constructs this same type and drives the same route logic
through it, so "the CLI adds zero privileged paths" (D-IMPL-22) is a
structural fact — both fronts hold the identical handle set, and a
capability absent from this bundle exists on neither surface.

Every field is an injected Protocol or factory handle the deployment's
composition root supplies. The bundle holds no bind address, no tenant and no
threshold — that is what CINV-01 is about here, and it is undisturbed.
Construction is keyword-only and the frozen dataclass cannot grow state after
boot.

**Four handles are required and five default to ``None``** (``D-IMPL-126``
item (3), Dave, 2026-08-13). ``control_plane``, ``artifact_store`` and
``product_resolver`` are read by four routers, two and one respectively, and no
useful app omits any of them. The other five gate exactly one noun each, and a
deployment exposing one noun should not have to fabricate seven handles to
serve it — the papercut the item (3) spike measured. On those five, ``None`` is
the positive assertion *this deployment exposes no such route*, and the route
refuses rather than serving half-wired.

**The tradeoff, stated rather than left to be discovered.** Before this, a
deployment that forgot a handle failed at *boot* with a ``TypeError``; after
it, the failure moves to *first call* as a typed 503 carrying
:data:`~ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT`. The mitigation
is that the 503 names the exact absent field and the exact argument to supply,
so the diagnostic is **relocated, not lost** — but a deployment that was
relying on the boot ``TypeError`` as its wiring check should assert its bundle
explicitly instead. This change is not free and is not presented as free.

What is deliberately NOT here: any graph read or write handle. The routes
reach the fabric only through the same factories and Control Plane actions
any client uses — there is no field on this bundle that could hold a route
into L2 or L3 (INV-CH7-10; T-07-23/T-07-25).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure.index import ErasureIndexProtocol
from ccf.erasure.trust import ErasureTrust
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

    Each entry below names the **routes the handle gates**, so a deployment
    deciding what to wire reads one docstring rather than three route modules.

    Attributes:
        control_plane: The registry agent declarations register into and
            config/workflow/status reads resolve through (the same audited
            Control Plane actions any client takes — T-07-25). **Required.**
            Gates the ``agent`` router entire, the ``config`` router entire,
            the ``skill`` router's grant verb and the ``workflow`` router's
            status read.
        artifact_store: The store the artifact and replay nouns read and
            write through (CLAUDE.md §7.4; D-IMPL-26). **Required.** Gates
            the ``replay`` and ``artifact`` routers entire.
        erasure_index: The durable erasure index the store is composed over
            (SEC-009; `D-IMPL-374` (4), C1). **Required.**
        erasure_trust: The per-tenant erasure authorities the composed store
            verifies erasures against — for each tenant that may erase, the
            HITL policy key its HITL transport is bound to, the content hash
            of its erasure workflow, and the erasure door's public key
            (SEC-009; `D-IMPL-374` (4), fix round 5, R1, R2, R4).
            **Required.**
        product_resolver: The deployment's assemble-and-gate path, exactly
            the seam the MCP egress server holds
            (:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`).
            **Required.** Gates the ``product`` router — the one noun a
            minimal deployment exists to serve.
        workflow_factory: The ONLY construction path to an executable
            workflow handle (ORCH-01 — the invoke route never touches a
            raw definition). **Optional, default ``None``.** Gates the
            ``workflow`` router's ``POST /invocations`` and
            ``POST /resumptions``; ``None`` asserts *this deployment exposes
            no workflow invocation*, and both routes refuse with a typed 503
            rather than serving half-wired.
        workflow_engine: The execution half the invoke/resume routes
            delegate to (:mod:`ccf_runtime.workflow.engine`). **Optional,
            default ``None``.** Gates the same two ``workflow`` routes;
            ``None`` asserts the same thing and refuses the same way.
        hitl_transport: The typed queue the hitl noun views and submits
            through (D-IMPL-20 — the authority path, never a notification
            channel). **Optional, default ``None``.** Gates the ``hitl``
            router's ``GET /queue`` and ``POST /actions``; ``None`` asserts
            *this deployment routes no human-in-the-loop traffic here*.
        skill_catalog: Discovery over the Control Plane (D-IMPL-12).
            **Optional, default ``None``.** Gates the ``skill`` router's
            ``GET /catalog`` and ``POST /catalog``; ``None`` asserts *this
            deployment publishes no skill catalog*.
        clock: The injected clock the hitl noun's action route stamps
            ``action_time`` from (D-IMPL-353 §2 P6); ``None`` gates that route
            with the typed 503 like every other optional handle.
        grant_ledger: The two-tier grant machinery the skill noun's
            mutating verb routes through (CLAUDE.md §6.2 channel 2).
            **Optional, default ``None``.** Gates the ``skill`` router's
            ``POST /grants`` and ``POST /revocations``; ``None`` asserts
            *this deployment issues no grants over HTTP*.
    """

    control_plane: ControlPlaneRegistry
    artifact_store: ArtifactStoreProtocol
    #: SEC-009 (`D-IMPL-374` (4), fix round 1 C1): the deployment's durable
    #: erasure index. **Required, no default**: ``create_app`` composes the
    #: store with the erasure consult over it, and a composition without a
    #: declared index refuses by name.
    erasure_index: ErasureIndexProtocol
    #: SEC-009 (`D-IMPL-374` (4), fix round 5, R1, R2, R4): the deployment's
    #: erasure trust root, per tenant — the HITL policy key each tenant's
    #: transport is bound to, its erasure workflow's content hash and the
    #: erasure door's public key. A tenant it names no authority for has every
    #: erasure read ``index-unsupported``. **Required, no default** (CINV-01).
    erasure_trust: ErasureTrust
    product_resolver: ProductResolverProtocol
    workflow_factory: WorkflowFactory | None = None
    workflow_engine: WorkflowEngine | None = None
    hitl_transport: HITLTransportProtocol | None = None
    skill_catalog: SkillCatalog | None = None
    grant_ledger: GrantLedger | None = None
    #: The injected clock the hitl noun's ``POST /actions`` stamps
    #: ``action_time`` from (D-IMPL-353 §2 P6) — never a wall clock in the
    #: handler and never the body. Optional like every other handle here:
    #: ``None`` asserts this deployment routes no human-in-the-loop traffic
    #: through this API, and the route refuses with the typed 503.
    clock: Callable[[], datetime] | None = None
