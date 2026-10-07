"""``create_app`` — the v0 HTTP API skeleton (EXPR-03; D-IMPL-22/23).

SDK-defined framing per CLAUDE.md §8.3 (the HTTP API as one of the three
v0 Experience Layer front doors). The app mirrors the D-IMPL-22/23 ruled
noun set exactly — ``agent``, ``skill``, ``workflow``, ``hitl``,
``replay``, ``artifact``, ``product``, ``config``, ``schema`` — plus
health and the generated OpenAPI document; the routes take and return the
SDK's existing ``extra=forbid`` contracts directly, so ``app.openapi()``
*is* the contract schema, with serialization and routing added and no new
semantics.

**What this server cannot do.** It cannot write to the graph: it holds no
graph handle of any kind, and neither does the
:class:`~ccf_runtime.http_api.dependencies.ApiDependencies` bundle it is
built over — there is no field anywhere on this surface that could hold a
route into L2 or L3, and L1 ingestion is deliberately absent from the noun
set by ruling (D-IMPL-23: a generic write endpoint would invite a second
writer path). It cannot mint authority either: every route delegates to
the same factories and Control Plane actions any in-process client uses,
so nothing is reachable over HTTP that is not reachable — identically
governed and identically audited — without it (T-07-25). And it does not
host itself: :func:`create_app` returns an application, never a server —
no bind address, tenant, or threshold exists in this package, and choosing
an interface would be choosing an exposure surface (T-06-14; CINV-01).

**Authority is required, and the insecure default is gone** (``SEC-001``;
supersedes D-IMPL-73). The ruling that permitted shipping this app
unauthenticated behind a ``CcfInsecureDefaultWarning`` has been withdrawn:
nothing has shipped, so the correct change is available rather than the
compatible one. There is no ``auth=None`` arm, no ``authorizer=None`` arm and
no ``acknowledge_insecure_default`` kwarg. The warning classes are deleted
with them — a warning nothing in CI escalates is a comment with a stack trace,
and this repository was measured to hold **zero** ``filterwarnings`` directives
that would have turned it into a failure.

Three further parameters were optional *because* D-IMPL-73 was: an entitlement
seam that were required would have made the acknowledged insecure posture
unbuildable. With that posture deleted, their reason went with it, so
``product_entitlement``, ``perspective_resolver`` and ``refusal_recorder`` are
required too. Each door they govern used to carry a per-request ``503`` for
the configuration in which they were absent; those branches are gone, because
the configuration is.

**The gate is total and has no carve-outs** (:mod:`ccf_runtime.http_api.gate`).
Every request — documentation routes, 404s, trailing-slash redirects,
malformed bodies, liveness — is authenticated and authorized before routing.
``create_app`` **refuses to build** an application containing a route that
declares no action id, which is what makes that completeness a property of the
application rather than of a CI sweep somebody might not run.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TypedDict

from fastapi import FastAPI

from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.erasure import compose_erasure_consult
from ccf.products.resolver import RefusalRecorderProtocol
from ccf_runtime.authz.delivery_boundary import (
    disclosing_boundary,
    recorded_boundary,
)
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
)
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf_runtime.authz.refusals import (
    ACTION_DOCS_READ,
    ACTION_HEALTH_READ,
    ACTION_OPENAPI_READ,
)
from ccf_runtime.authz.route_declaration import (
    ResourceBinding,
    authorizes,
    route_authorization,
)
from ccf_runtime.http_api.auth import HttpAuthProtocol
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.gate import AuthorizationGate, build_route_table
from ccf_runtime.http_api.routes import (
    agent,
    artifact,
    backends,
    config,
    hitl,
    product,
    replay,
    schema,
    skill,
    workflow,
)

__ccf_mode__ = "algorithmic"

__all__ = ["AUTH_POSTURE_SENTENCE", "GovernedWiringError", "HttpAuthority", "create_app"]

#: What the surface is, mechanism only (CINV-01 — no deployment vocabulary).
_MECHANISM_LINE = (
    "Typed HTTP front door over the fabric's existing extra=forbid"
    " contracts, mirroring the D-IMPL-22/23 ruled noun set (CLAUDE.md"
    " §8.3; EXPR-03)."
)

#: The auth posture, stated in the served document as the v0 sentence once
#: was — and now stating the opposite thing (``SEC-001``). It is carried
#: verbatim in the OpenAPI ``info.description`` and pinned by test as the
#: string it is, exactly as its predecessor was: an adopter reading the
#: document learns the posture from the document.
AUTH_POSTURE_SENTENCE = (
    "Every request to this API is authenticated and authorized before it is"
    " routed: there is no unauthenticated arm, no path is exempt, every route"
    " declares the action identifier its authorization is decided under, and"
    " what each action reaches is the deployment's own versioned scope"
    " mapping rather than any default this API ships."
)


class HttpAuthority(TypedDict):
    """The five seams :func:`create_app` requires, as one typed bundle.

    For embedders that build the app somewhere other than a deployment's own
    composition — the CLI's in-process leg (:func:`ccf_runtime.cli.main.main`),
    a test fixture — and hand the seams along as a unit. Every key is required
    and every value type is the seam's own, so a bundle missing a seam is a
    type error where the bundle is written, and ``**bundle`` at
    :func:`create_app` is checked key by key. This replaces the one call site
    that carried ``# type: ignore[arg-type]`` over an untyped mapping
    (``D-IMPL-353`` §4 rule 6).
    ``tests/cli/test_authority_bundle.py::test_the_bundle_names_exactly_create_apps_keyword_seams``
    holds the keys and types equal to :func:`create_app`'s keyword seams, so
    the two cannot drift apart.
    """

    auth: HttpAuthProtocol
    authorizer: TenantAuthorizerProtocol
    product_entitlement: ProductEntitlementSourceProtocol
    perspective_resolver: PerspectiveResolverProtocol
    refusal_recorder: RefusalRecorderProtocol


class GovernedWiringError(ValueError):
    """The recorder and the store it writes through disagree about authority.

    D-IMPL-353 §3: ``create_app`` refuses mismatched wiring at boot rather than
    at the first denial. A recorder naming a replay record class over a store
    whose :class:`~ccf.artifacts.protocol.WriteKinds` declaration does **not**
    name that class under ``ReplayMint`` — or over a store exposing no
    declaration at all — would build cleanly and then fail to record the first
    governed determination it is asked to record — which ``D-IMPL-256`` (2)
    names as *not a valid governed door*, and which would surface only when a
    denial happened, making auditability contingent on outcome.

    A :class:`ValueError`, on this codebase's construction-refusal posture
    (*"prefer fail-at-construction/boot where practical"*).
    """


def governed_wiring(*, refusal_recorder: object, builder: str) -> None:
    """Refuse a recorder whose store does not admit its writer (D-IMPL-353 §3).

    Reads the two facts the SDK's own recorder states about itself —
    ``replay_record_class`` and ``artifact_store`` — and the
    :class:`~ccf.artifacts.protocol.WriteKinds` declaration the store carries.
    The recorder's writer holds ``Authorized[ReplayMint]`` for its record class
    (§2 P3), and a store admits a write to a class only under the kinds the
    deployment declared for it: a class the store does not declare is the
    client lane and requires ``ArtifactWrite``, which the fabric's own writer
    never holds. So a recorder naming a replay class over a store that has not
    declared that class under ``ReplayMint`` would build cleanly and then fail
    to record the first governed determination it is asked to record — which
    ``D-IMPL-256`` (2) names as *not a valid governed door*, and which would
    surface only when a denial happened, making auditability contingent on
    outcome. It is refused here, at boot, instead — the join's reading of the
    "second direction" Lane CAP-GATE left for the per-class write-kind mapping.

    A recorder that states neither fact names no class over no store, so there
    is nothing to mismatch and nothing is checked (a third-party recorder
    conforming to the Protocol alone). A store that exposes **no** declaration
    is refused: the app cannot show the recorder's writer is admitted, and
    *don't know* is not *pass*.

    Args:
        refusal_recorder: What the builder was handed.
        builder: The builder's own name, for the message.

    Raises:
        GovernedWiringError: the store exposes no write-kinds declaration, or
            its declaration does not name the recorder's class under
            ``ReplayMint``.
    """
    record_class = getattr(refusal_recorder, "replay_record_class", None)
    store = getattr(refusal_recorder, "artifact_store", None)
    if not isinstance(record_class, str) or store is None:
        return
    declaration = getattr(store, "write_kinds", None)
    if not isinstance(declaration, WriteKinds):
        raise GovernedWiringError(
            f"{builder} was handed a refusal_recorder that files"
            f" {record_class!r} through a store of type"
            f" {type(store).__name__} exposing no `write_kinds` declaration;"
            " the app cannot show the recorder's ReplayMint writer is"
            " admitted, and a door that cannot record what it decides is not"
            " a valid governed door (D-IMPL-256 (2); D-IMPL-353 §3). Both"
            " shipped stores take `write_kinds=` at construction and expose it"
        )
    if ReplayMint not in declaration.for_class(record_class):
        raise GovernedWiringError(
            f"{builder} was handed a refusal_recorder that files"
            f" {record_class!r} through a store whose write-kinds declaration"
            f" does not name that class under ReplayMint ({declaration!r});"
            " its first governed determination would fail to record, and a"
            " door that cannot record what it decides is not a valid governed"
            " door (D-IMPL-256 (2); D-IMPL-353 §3). Declare the class at"
            " composition — WriteKinds.declare({" + repr(record_class)
            + ": (ReplayMint,)}) — on the store the doors serve from"
        )


def create_app(
    deps: ApiDependencies,
    *,
    auth: HttpAuthProtocol,
    authorizer: TenantAuthorizerProtocol,
    product_entitlement: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> FastAPI:
    """Build the skeleton over ``deps`` — built, never hosted.

    Args:
        deps: The named provider bundle carrying every injected fabric
            handle (the same type the CLI's ``--local`` mode constructs).
        auth: The authentication hook (:mod:`ccf_runtime.http_api.auth`).
            **Required**: the gate has no arm in which authentication is
            skipped, so there is no value of this parameter that produces an
            unauthenticated application (``SEC-001``).
        authorizer: The authorizer every request is decided by
            (:class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol`).
            **Required**, and the SDK ships exactly one implementation —
            :class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`,
            which is deny-by-default and needs a registered scope mapping at a
            pinned version. There is deliberately no permissive or dev
            authorizer anywhere in the library to pass here.
        product_entitlement: The per-principal product entitlement seam.
            **Required.** It was optional only because the unauthenticated
            posture had to stay buildable; with that posture deleted there is
            no configuration in which a product door decides nothing, and the
            per-request ``503`` that represented one is deleted with it.
        perspective_resolver: The role-derivation seam, supplied with
            ``product_entitlement``. **Required**, same reason: a door that
            cannot name the Π conditioning a product is shaped under must not
            serve one, and now it cannot be built.
        refusal_recorder: The deployment's ONE minting seam
            (:class:`~ccf.products.resolver.RefusalRecorderProtocol`).
            **Required**, and checked at construction: ``D-IMPL-256`` (2) rules
            that *a door configured to make governed determinations without the
            ability to record them is not a valid governed door*, so
            :func:`~ccf_runtime.authz.delivery_boundary.recorded_boundary` and
            :func:`~ccf_runtime.authz.delivery_boundary.disclosing_boundary`
            run here and refuse rather than building. There is deliberately no
            warn-and-serve posture and no per-request refusal: failing closed
            only on denial would make auditability contingent on outcome.

    **The erasure consult is composed always** (SEC-009; ``D-IMPL-374`` (4),
    U12): the store ``deps`` carries is wrapped in
    :class:`~ccf.erasure.ErasureConsultingStore` over the registry mirror of
    ``deps.control_plane``, so no route can serve an erased address's bytes;
    on an empty index it is identity.

    Returns:
        A configured ``FastAPI`` application. Deliberately not started and
        bound to nothing — hosting is the deployment's decision.

    Raises:
        UnrecordableDeliveryBoundaryError: ``refusal_recorder`` cannot record
            a governed determination, or cannot state a disclosure level.
        GovernedWiringError: ``refusal_recorder`` files a class its store has
            not declared under ``ReplayMint``, or its store exposes no
            write-kinds declaration (D-IMPL-353 §3).
        ~ccf_runtime.http_api.gate.UndeclaredRouteError: a mounted route
            declares no action id, or declares an action no capability kind
            exists for. The message names every one of them.
    """
    # `D-IMPL-256` (2), before anything else is built: an entitling door with
    # no way to record what it decides is not built at all.
    recorded_boundary(refusal_recorder=refusal_recorder, builder="create_app")
    # `D-IMPL-345` R-2, in the same breath and for the same reason: the two
    # evidence-read routes disclose at the level the recorder that disclosed
    # the serve would state, so a recorder that cannot state one cannot govern
    # them.
    evidence_recorder = disclosing_boundary(
        refusal_recorder=refusal_recorder, builder="create_app"
    )
    # D-IMPL-353 §3, still before anything is built: a recorder that could
    # not record its first governed determination — its store has not
    # declared its class under ReplayMint — is refused here, not there.
    # (Placed after the two `D-IMPL-345` checks so their anchored text, which
    # `tests/http_api/test_product_refusal_statuses.py` severs by literal, is
    # unchanged.)
    governed_wiring(refusal_recorder=refusal_recorder, builder="create_app")

    # SEC-009 (`D-IMPL-374` (4), U12): the erasure consult is composed ALWAYS,
    # around whatever store the deployment handed in, so every route reads
    # through it; on an empty index it is identity.
    deps = replace(
        deps,
        artifact_store=compose_erasure_consult(
            deps.artifact_store,
            index=deps.erasure_index,
            audit_log=deps.control_plane.audit_log,
            # The door's determination clock (ruling 3): the one the entitled
            # reads are already stamped with.
            clock=product_entitlement.clock,
        ),
    )

    app = FastAPI(
        title="CCF HTTP API",
        description=f"{_MECHANISM_LINE} {AUTH_POSTURE_SENTENCE}",
    )

    _declare_generated_routes(app)

    app.include_router(agent.build_router(deps), prefix="/agent")
    app.include_router(skill.build_router(deps), prefix="/skill")
    app.include_router(workflow.build_router(deps), prefix="/workflow")
    app.include_router(hitl.build_router(deps), prefix="/hitl")
    # `D-IMPL-345`: the two evidence-read routes are governed dereferences, so
    # they receive the same seams the product route does — the entitlement
    # source that decides, and the recorder that mints and states the level,
    # both checked at construction above.
    app.include_router(
        replay.build_router(
            deps,
            entitlement_source=product_entitlement,
            refusal_recorder=evidence_recorder,
        ),
        prefix="/replay",
    )
    app.include_router(
        artifact.build_router(
            deps,
            entitlement_source=product_entitlement,
            refusal_recorder=evidence_recorder,
        ),
        prefix="/artifact",
    )
    app.include_router(
        product.build_router(
            deps,
            entitlement_source=product_entitlement,
            perspective_resolver=perspective_resolver,
            refusal_recorder=refusal_recorder,
        ),
        prefix="/product",
    )
    app.include_router(config.build_router(deps), prefix="/config")
    app.include_router(schema.build_router(deps), prefix="/schema")
    app.include_router(backends.build_router(deps), prefix="/backends")

    @app.get("/health", summary="Liveness (D-IMPL-23)")
    @authorizes(ACTION_HEALTH_READ, resource=ResourceBinding.route())
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Built from the FULLY mounted application and BEFORE the gate is
    # installed, so the table the gate decides from and the routes the app
    # actually serves are the same enumeration. This is the line that refuses
    # to return an application with an undeclared route on it.
    table = build_route_table(app)
    app.add_middleware(
        AuthorizationGate, auth=auth, authorizer=authorizer, table=table
    )
    return app


def _declare_generated_routes(app: FastAPI) -> None:
    """Give FastAPI's own routes the declarations their authors could not.

    ``/openapi.json``, ``/docs``, ``/docs/oauth2-redirect`` and ``/redoc`` are
    built inside ``FastAPI.setup()``, so there is no definition site of ours to
    decorate. They are declared here instead — which is still *this
    application's* code declaring them, and still one declaration per mounted
    route. The alternative, a carve-out list in the gate, would be the
    applicability switch this design exists to remove.

    Called immediately after construction, so the only routes it can see are
    FastAPI's own; every router mounted afterwards carries declarations from
    its own handlers, and the ``is not None`` check leaves those untouched.

    **The fallback is the safe direction.** A route matching the app's
    ``openapi_url`` takes the document action; anything else FastAPI generates
    takes the documentation action. A future FastAPI route absorbed by that
    fallback is a *gated* route under an action a deployment must have granted
    — it can never become an open one.
    """
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None or route_authorization(endpoint) is not None:
            continue
        action = (
            ACTION_OPENAPI_READ
            if getattr(route, "path", None) == app.openapi_url
            else ACTION_DOCS_READ
        )
        authorizes(action, resource=ResourceBinding.route())(endpoint)
