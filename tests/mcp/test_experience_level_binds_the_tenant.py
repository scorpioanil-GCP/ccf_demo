"""The Experience door's erasure branch reads the level in force for the caller's tenant and principal together.

The adjacent sweep of Dave's ruling of 2026-10-07 (``D-IMPL-378``; the finding
and the ruling are stated in ``tests/mcp/test_read_refusal_attribution_mcp.py``):
every lookup that keys a disclosure decision on a principal id must key it on
the tenant beside it. The Experience door answers an erasure a seam met by
level (FW-3; ``D-IMPL-374``): ``minimal`` is the opaque
``ccf-runtime-failure:<id>`` — those tools have no not-found rendering — and
above it the recorded ``erased-content`` shell. Which branch a caller takes was
read under the door RECORDER's tenant, keyed by the principal id alone, while
the shell itself is disclosed under the tenant the determination was made under
(the recorder's own lookup, ``D-IMPL-378``). On a door serving several tenants
through one recorder, a caller of another tenant therefore took the branch the
recorder's tenant declares for a colliding principal id: at its own
``minimal`` it received a shell where its tenant's callers receive the opaque
failure, and at its own ``full`` it received the opaque failure.

Tenant, principal, class and scope names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import pathlib
from typing import Any

import anyio
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.mcp.auth import TENANT_CLAIM
from tests.http_api.composition_authority import deployment_store, refusal_recorder, register_typed_at_composition
from tests.mcp.guarded_servers import (
    AUDIT_INSTANT,
    FOREIGN,
    PRINCIPAL,
    PRODUCT_CLASS,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    _auth,
    _perspective,
    _verifier,
    authorizer_granting,
)
from tests.mcp.test_fw3_erasure_at_mcp_doors import OPAQUE, _erased, _no_disclosure, _raising


def _door(tmp_path: pathlib.Path, *, own_level: str, foreign_level: str) -> Any:
    """``get_context`` over a seam that meets an erasure; ONE recorder of ``TENANT``; both tenants admitted.

    ``PRINCIPAL`` is a principal of both tenants, entitled to the class in each,
    at ``own_level`` in ``TENANT`` and ``foreign_level`` in ``FOREIGN``.
    """
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL, ExperienceProductNotServable, build_experience_server

    registry = ControlPlaneRegistry()
    for tenant, level in ((TENANT, own_level), (FOREIGN, foreign_level)):
        register_typed_at_composition(
            registry,
            product_entitlement_key(tenant_id=tenant),
            ProductEntitlementPolicy(
                tenant_id=tenant,
                policy_version="1.0.0",
                principals={
                    PRINCIPAL: ProductEntitlementGrant(
                        permitted_schema_names=frozenset({PRODUCT_CLASS}),
                        permitted_roles=frozenset({"role-guard"}),
                        disclosure_level=level,
                    )
                },
            ),
            PRODUCT_ENTITLEMENT_POLICY,
        )
    source = ControlPlaneProductEntitlementSource(control_plane=registry, clock=lambda: AUDIT_INSTANT)
    recorder = refusal_recorder(
        registry,
        store=deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS),
        tenant=TENANT,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    return build_experience_server(
        server_name="experience-level-binds-the-tenant",
        product_resolver=_raising(ExperienceProductNotServable("absent")),
        context_provider=_raising(_erased()),
        get_context_description="the tenant binding",
        entitled_product_class=PRODUCT_CLASS,
        tool_allowlist=frozenset({GET_CONTEXT_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(tenants=(TENANT, FOREIGN)),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )


def _get_context_as_foreign(server: Any) -> tuple[str | None, BaseException | None]:
    """``PRINCIPAL``, verified for ``FOREIGN`` only, asks ``get_context`` under ``FOREIGN``."""
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(token="in-process", client_id=PRINCIPAL, scopes=[SCOPE], claims={TENANT_CLAIM: [FOREIGN]})
        )
    )
    try:
        result = anyio.run(server.call_tool, GET_CONTEXT_TOOL, {"tenant": FOREIGN, "entity": "any"})
    except Exception as raised:  # noqa: BLE001 - the subject under test
        return None, raised
    finally:
        auth_context_var.reset(reset)
    if isinstance(result, tuple):
        result = result[0]
    return "".join(block.text for block in result if hasattr(block, "text")), None


def test_the_erasure_branch_reads_the_level_in_force_for_the_callers_tenant_not_the_recorders(
    tmp_path: pathlib.Path,
) -> None:
    """``FOREIGN``'s caller at ``minimal`` receives the opaque failure its own
    posture requires, whatever ``TENANT`` declares for the same principal id;
    and at its own ``full``, the ``erased-content`` shell at ``full``."""
    served, raised = _get_context_as_foreign(
        _door(tmp_path / "upgrade", own_level=DISCLOSURE_FULL, foreign_level=DISCLOSURE_MINIMAL)
    )
    assert served is None and raised is not None, (
        "the recorder's tenant's level for a colliding principal id chose the Experience door's erasure branch"
        f" for another tenant's caller: {served!r}"
    )
    _no_disclosure(str(raised))
    assert OPAQUE.match(str(raised)), str(raised)

    served, raised = _get_context_as_foreign(
        _door(tmp_path / "downgrade", own_level=DISCLOSURE_MINIMAL, foreign_level=DISCLOSURE_FULL)
    )
    assert raised is None, repr(raised)
    shell = RefusalEnvelope.model_validate_json(served or "")
    assert (shell.kind, shell.disclosure) == ("erased-content", DISCLOSURE_FULL), shell
