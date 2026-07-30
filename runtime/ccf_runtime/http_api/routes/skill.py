"""The ``skill`` noun — catalog discovery and governed grants (D-IMPL-23).

The mutating verb routes through the two-tier
:class:`~ccf.skills.grants.GrantLedger` exactly as any client's would
(CLAUDE.md §6.2 channel 2): the agent definition is resolved from the
Control Plane by pinned key and version — never carried inline — and a
tier-1 or registration refusal returns as its typed body under 409, wrapped
with a ``kind`` discriminator so a wire consumer can tell the two refusal
families apart without parsing prose.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneMissing, RegistrationRefusal
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.grants import GrantRefusal, SkillGrant
from ccf_runtime.http_api.dependencies import ApiDependencies

__ccf_mode__ = "algorithmic"

__all__ = ["GrantIssued", "GrantRequest", "build_router"]


class GrantRequest(CCFContract):
    """One grant request: the grant artifact plus its pinned definition ref."""

    grant: SkillGrant
    definition_key: str
    definition_version: str
    actor: str


class GrantIssued(CCFContract):
    """The issued outcome — the grant's content hash, its D-07 identity."""

    grant_hash: str


def build_router(deps: ApiDependencies) -> APIRouter:
    """The skill router over the injected catalog and ledger."""
    router = APIRouter()

    @router.get(
        "/catalog",
        response_model=list[SkillCatalogEntry],
        summary="Skill catalog (D-IMPL-23)",
    )
    def catalog() -> list[SkillCatalogEntry]:
        return list(deps.skill_catalog.discover())

    @router.post(
        "/grants",
        response_model=GrantIssued,
        summary="Skill grant (D-IMPL-23)",
    )
    def grant(request: GrantRequest) -> GrantIssued | JSONResponse:
        try:
            artifact = deps.control_plane.resolve(
                request.definition_key, request.definition_version
            )
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        definition = AGENT_DEFINITION.validate(artifact)
        assert isinstance(definition, AgentDefinition)
        outcome = deps.grant_ledger.request(
            request.grant, definition=definition, actor=request.actor
        )
        if isinstance(outcome, (GrantRefusal, RegistrationRefusal)):
            kind = (
                "grant-refusal"
                if isinstance(outcome, GrantRefusal)
                else "registration-refusal"
            )
            return JSONResponse(
                status_code=409,
                content={
                    "kind": kind,
                    "refusal_type": type(outcome).__name__,
                    "refusal": json.loads(canonical_bytes(outcome)),
                },
            )
        return GrantIssued(grant_hash=outcome)

    return router
