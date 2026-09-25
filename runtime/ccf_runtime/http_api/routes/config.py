"""The ``config`` noun — Control Plane introspection (D-IMPL-22/23).

Reads only, and only through the registry's own introspection surface:
keys by artifact class, versions under a key, and pinned resolution — the
same versioned, audited artifacts every other Control Plane consumer
resolves. The SDK enumerates no class vocabulary here; ``class_id`` is the
caller's statement (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
)
from ccf.authz.capability import (
    ConfigKeysRead,
    ConfigRegister,
    ConfigResolve,
    ConfigVersionsRead,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import ArtifactClass, ArtifactLoadError, parse_artifact
from ccf.controlplane.registry import ControlPlaneMissing, RegistrationRefusal
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf_runtime.authz.refusals import (
    ACTION_CONFIG_KEYS_READ,
    ACTION_CONFIG_REGISTER,
    ACTION_CONFIG_RESOLVE,
    ACTION_CONFIG_VERSIONS_READ,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.grants import absent as absent_response
from ccf_runtime.http_api.grants import authorized_from_request, within_tenant
from ccf_runtime.http_api.routes import canonical_response

__ccf_mode__ = "algorithmic"

__all__ = ["ConfigRegistered", "ConfigRegistrationRequest", "build_router"]

#: The SDK-typed artifact classes the registration route interprets — the
#: same classes any in-process client registers through ``register_versioned``
#: (D-05). Mechanism identifiers, not domain values; deployment-declared
#: classes stay on the in-process ``register_typed`` path.
_TYPED_CLASSES: dict[str, ArtifactClass] = {
    artifact_class.class_id: artifact_class
    for artifact_class in (
        AGENT_DEFINITION,
        TASK_DEFINITION,
        PROMPT_ARTIFACT,
        WORKFLOW_DEFINITION,
    )
}


class ConfigRegistrationRequest(CCFContract):
    """One registration: key, SDK-typed class id, and the artifact document.

    Added for the D-IMPL-22 CLI surface (07-11): `ccf skill import` must
    register prompt artifacts through the same D-05 versioned path any
    client takes, over the wire — the CLI holds no registry handle.
    """

    key: str
    class_id: str
    artifact: dict[str, Any]


class ConfigRegistered(CCFContract):
    """The registered outcome — the key and its content-hash version."""

    key: str
    version: str


def build_router(deps: ApiDependencies) -> APIRouter:
    """The config router over the injected Control Plane."""
    router = APIRouter()

    @router.get(
        "/keys",
        response_model=list[str],
        summary="Config keys (D-IMPL-23)",
    )
    @authorizes(
        ACTION_CONFIG_KEYS_READ, resource=ResourceBinding.query("class_id")
    )
    def keys(class_id: str, request: Request) -> list[str]:
        authorized = authorized_from_request(request, kind=ConfigKeysRead)
        # The capability's tenant's keys, and no other tenant's (F-READ-03).
        return [
            key
            for key in deps.control_plane.keys_of_class(class_id)
            if within_tenant(tenant=authorized.tenant, key=key)
        ]

    @router.get(
        "/versions",
        response_model=list[str],
        summary="Config versions (D-IMPL-23)",
    )
    @authorizes(
        ACTION_CONFIG_VERSIONS_READ, resource=ResourceBinding.query("key")
    )
    def versions(key: str, request: Request) -> list[str]:
        authorized = authorized_from_request(request, kind=ConfigVersionsRead)
        if not within_tenant(tenant=authorized.tenant, key=key):
            return []  # another tenant's key has no versions here, exactly like an absent one
        return list(deps.control_plane.versions(key))

    @router.get("/resolution", summary="Config resolve (D-IMPL-23)")
    @authorizes(ACTION_CONFIG_RESOLVE, resource=ResourceBinding.query("key"))
    def resolution(key: str, version: str, request: Request) -> Response:
        authorized = authorized_from_request(request, kind=ConfigResolve)
        if not within_tenant(tenant=authorized.tenant, key=key):
            raise absent_response(key, version)  # another tenant's key reads as absent (F-READ-04)
        try:
            artifact = deps.control_plane.resolve(key, version)
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(artifact)

    @router.post(
        "/registrations",
        response_model=ConfigRegistered,
        summary="Config register (D-IMPL-22)",
    )
    # The ``SEC-002`` door, and the reason the resource axis exists: the key
    # this registration writes is the prompt artifact an agent then runs on,
    # so the decision is about WHICH key, not only about who is recognized.
    @authorizes(ACTION_CONFIG_REGISTER, resource=ResourceBinding.body("key"))
    def registration(
        body: ConfigRegistrationRequest, request: Request
    ) -> ConfigRegistered | JSONResponse:
        # D-IMPL-353 §1.4: the capability for THIS action, or nothing.
        authorized = authorized_from_request(request, kind=ConfigRegister)
        artifact_class = _TYPED_CLASSES.get(body.class_id)
        if artifact_class is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{body.class_id!r} is not an SDK-typed artifact"
                    " class this route interprets"
                ),
            )
        try:
            artifact = parse_artifact(body.artifact, artifact_class)
        except (ArtifactLoadError, ValueError) as bad:
            raise HTTPException(status_code=422, detail=str(bad)) from bad
        # §1.2: the key the registry writes IS `authorized.resource` — the
        # gate resolved it from the body's `key`; the handler supplies none.
        outcome = deps.control_plane.register_versioned(
            authorized, artifact, artifact_class
        )
        if isinstance(outcome, RegistrationRefusal):
            # wrapped with the refusal type name so a wire consumer can
            # tell the refusal families apart without parsing prose (the
            # same discipline as the grant route; T-07-26)
            return JSONResponse(
                status_code=409,
                content={
                    "kind": "registration-refusal",
                    "refusal_type": type(outcome).__name__,
                    "refusal": json.loads(canonical_bytes(outcome)),
                },
            )
        return ConfigRegistered(key=authorized.resource, version=outcome)

    return router
