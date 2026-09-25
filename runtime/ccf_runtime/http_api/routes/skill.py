"""The ``skill`` noun — catalog discovery and governed grants (D-IMPL-23).

The mutating verb routes through the two-tier
:class:`~ccf.skills.grants.GrantLedger` exactly as any client's would
(CLAUDE.md §6.2 channel 2): the agent definition is resolved from the
Control Plane by pinned key and version — never carried inline — and a
tier-1 or registration refusal returns as its typed body under 409, wrapped
with a ``kind`` discriminator so a wire consumer can tell the two refusal
families apart without parsing prose.

**The catalog entry's tenant may agree with the grant, never supply it.**
:class:`~ccf.skills.catalog.SkillCatalogEntry` declares a ``tenant``, and that
contract is not this door's to change — so the door refuses an entry naming
any tenant but the verified grant's (:func:`_own_tenant`), exactly as
``routes/hitl.py`` refuses a submission that does. Deleting the field at its
own contract is owed work in another tree, not something worked around here.

**The acting principal is derived, never typed (``SEC-002``).** Both mutating
verbs used to take an ``actor`` string in the request body, which made the
audited author of a grant or a revocation a value the caller wrote — the
identity defect ``D-IMPL-67`` had already closed one door down, where the HITL
submission's subject is derived from the verified
:class:`~ccf_runtime.mcp.auth.TokenGrant` and a conflicting claim is refused
rather than believed. The field is **deleted** rather than checked: a field
that must equal the verified identity has no remaining correct reading, and
leaving it would keep a second spelling of the author in the wire contract.
The audited actor is the **capability's principal** (D-IMPL-353 §1.2) —
``authorized.principal``, the verified ``client_id`` the gate minted for —
through the same ledger transition any in-process client takes.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.authz.capability import (
    Authorized,
    SkillCatalogRead,
    SkillCatalogRegister,
    SkillGrant as SkillGrantKind,
    SkillRevoke,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneMissing, RegistrationRefusal
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.grants import GrantRefusal, GrantTransitionError, SkillGrant
from ccf_runtime.authz.refusals import (
    ACTION_SKILL_CATALOG_READ,
    ACTION_SKILL_CATALOG_REGISTER,
    ACTION_SKILL_GRANT,
    ACTION_SKILL_REVOKE,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED, refusal_detail
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.http_api.routes import _required_handle

__ccf_mode__ = "algorithmic"

__all__ = [
    "GrantIssued",
    "GrantRequest",
    "GrantRevocationRequest",
    "build_router",
]


class GrantRequest(CCFContract):
    """One grant request: the grant artifact plus its pinned definition ref.

    No ``actor``: the audited requester is the verified caller (``SEC-002``;
    the ``D-IMPL-67`` derivation precedent). ``definition_key`` is this
    route's authorization resource, so a deployment states which agent
    definitions a scope may skill rather than granting the verb whole.
    """

    grant: SkillGrant
    definition_key: str
    definition_version: str


class GrantIssued(CCFContract):
    """The issued outcome — the grant's content hash, its D-07 identity."""

    grant_hash: str


class GrantRevocationRequest(CCFContract):
    """One revocation: the grant's D-07 identity, and nothing else.

    Added for the D-IMPL-22 CLI surface (07-11): §8.3 rules "skill
    grant/revoke" for the CLI, the CLI is a thin client with zero
    privileged paths, so the revoke verb requires this route — the same
    audited :meth:`~ccf.skills.grants.GrantLedger.revoke` transition any
    in-process client takes.

    No ``actor``: the audited revoker is the verified caller (``SEC-002``).
    """

    grant_hash: str


def _own_tenant(
    authorized: Authorized[SkillCatalogRegister], declared: str
) -> None:
    """Refuse an entry that declares a tenant other than the capability's.

    ``SEC-002``. :class:`~ccf.skills.catalog.SkillCatalogEntry` carries a
    ``tenant`` field, and the field lives in ``src/ccf/skills/catalog.py``
    rather than here — so this door cannot delete it the way it deleted
    ``actor``. What it can do is refuse to act on it, which is the same
    posture ``routes/hitl.py`` takes for the submission tenant it also cannot
    delete: the caller-supplied value may only **agree** with the verified
    grant, and a disagreement never reaches the catalog.

    Refusing rather than rewriting, deliberately: a door that silently
    replaced the caller's tenant would register an entry under a name nobody
    asked for and report success.

    Raises:
        HTTPException: 403 carrying
            :data:`~ccf_runtime.http_api.errors.ERROR_TENANT_UNAUTHORIZED`.
    """
    if declared != authorized.tenant:
        raise HTTPException(
            status_code=403,
            detail=refusal_detail(
                error_code=ERROR_TENANT_UNAUTHORIZED,
                message=(
                    "the entry declares a tenant other than the one the"
                    " verified grant acts for; the tenant is the grant's and"
                    " a door never takes it from the body (SEC-002)"
                ),
            ),
        )


def build_router(deps: ApiDependencies) -> APIRouter:
    """The skill router over the injected catalog and ledger."""
    router = APIRouter()

    @router.get(
        "/catalog",
        response_model=list[SkillCatalogEntry],
        summary="Skill catalog (D-IMPL-23)",
    )
    @authorizes(ACTION_SKILL_CATALOG_READ, resource=ResourceBinding.route())
    def catalog(request: Request) -> list[SkillCatalogEntry]:
        authorized_from_request(request, kind=SkillCatalogRead)
        # Narrowed once per body (D-IMPL-126 item (3)): a deployment that
        # publishes no skill catalog wired none, and this route refuses with a
        # typed 503 naming the field rather than dereferencing `None`.
        catalog_handle = _required_handle(
            deps.skill_catalog,
            field="skill_catalog",
            routes="skill catalog discovery",
        )
        return list(catalog_handle.discover())

    @router.post(
        "/catalog",
        summary="Skill catalog register (D-IMPL-22)",
    )
    @authorizes(
        ACTION_SKILL_CATALOG_REGISTER, resource=ResourceBinding.body("name")
    )
    def register_entry(
        entry: SkillCatalogEntry, request: Request
    ) -> JSONResponse:
        authorized = authorized_from_request(request, kind=SkillCatalogRegister)
        _own_tenant(authorized, entry.tenant)
        catalog_handle = _required_handle(
            deps.skill_catalog,
            field="skill_catalog",
            routes="skill catalog registration",
        )
        outcome = catalog_handle.register(entry)
        if isinstance(outcome, RegistrationRefusal):
            return JSONResponse(
                status_code=409,
                content={
                    "kind": "registration-refusal",
                    "refusal_type": type(outcome).__name__,
                    "refusal": json.loads(canonical_bytes(outcome)),
                },
            )
        return JSONResponse(content={"name": entry.name, "version": outcome})

    @router.post(
        "/grants",
        response_model=GrantIssued,
        summary="Skill grant (D-IMPL-23)",
    )
    @authorizes(
        ACTION_SKILL_GRANT, resource=ResourceBinding.body("definition_key")
    )
    def grant(
        body: GrantRequest, request: Request
    ) -> GrantIssued | JSONResponse:
        # D-IMPL-353 §1.4: `Authorized[SkillGrant]` for THIS definition key.
        authorized = authorized_from_request(request, kind=SkillGrantKind)
        assert authorized.resource == body.definition_key
        ledger = _required_handle(
            deps.grant_ledger,
            field="grant_ledger",
            routes="skill grant issuance",
        )
        try:
            artifact = deps.control_plane.resolve(
                body.definition_key, body.definition_version
            )
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        definition = AGENT_DEFINITION.validate(artifact)
        assert isinstance(definition, AgentDefinition)
        # JOIN (§1.2, Lane HANDLES): `ledger.request(authorized, grant,
        # definition=...)` — `actor` is deleted; the actor is
        # `authorized.principal`. Left on today's signature with that value.
        outcome = ledger.request(
            body.grant, definition=definition, actor=authorized.principal
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

    @router.post(
        "/revocations",
        response_model=GrantRevocationRequest,
        summary="Skill revoke (D-IMPL-22)",
    )
    @authorizes(
        ACTION_SKILL_REVOKE, resource=ResourceBinding.body("grant_hash")
    )
    def revoke(
        body: GrantRevocationRequest, request: Request
    ) -> GrantRevocationRequest:
        # D-IMPL-353 §1.4: `Authorized[SkillRevoke]`, its own kind — revoking
        # is deliberately not the granting action (see `refusals`).
        authorized = authorized_from_request(request, kind=SkillRevoke)
        assert authorized.resource == body.grant_hash
        ledger = _required_handle(
            deps.grant_ledger,
            field="grant_ledger",
            routes="skill grant revocation",
        )
        try:
            # JOIN (§1.2, Lane HANDLES): `ledger.revoke(authorized, grant_hash)`
            # — `actor` is deleted. Left on today's signature with the
            # capability's principal.
            ledger.revoke(body.grant_hash, actor=authorized.principal)
        except GrantTransitionError as refused:
            raise HTTPException(
                status_code=409, detail=str(refused)
            ) from refused
        return body

    return router
