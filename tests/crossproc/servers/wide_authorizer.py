"""A real, deny-by-default authorizer granting the named scopes everything.

Every MCP builder takes a required ``authorizer`` (``D-IMPL-353`` §1.1 — the
wrapper is the MCP mint site and asks it before any body runs). The child
servers and cross-process tests in this package exist to measure entitlement,
disclosure and the wire, never authorization, so each composes this one: a
real :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` at a real
pinned version, interpreted by the real
:class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`. The SDK
ships no permissive authorizer and this module is not one either — the grant
is spelled out as prefix globs on both axes because the D-01 grammar refuses
``"*"``, so a reader can see it is a fixture posture.

Duplicated from ``tests/mcp/guarded_servers.py`` rather than imported, because
a child spawned as a bare ``python <file>`` puts ``tests/`` on its path, where
``tests/mcp`` would shadow the ``mcp`` library.
"""

from __future__ import annotations

import string
from collections.abc import Iterable
from datetime import UTC, datetime

from ccf.authz import actions
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from http_api.composition_authority import register_typed_at_composition

MAPPING_KEY = "crossproc/scope-mapping"
ALL_ACTIONS: tuple[str, ...] = tuple(getattr(actions, name) for name in actions.__all__)
WIDE: tuple[str, ...] = tuple(
    f"{character}*"
    for character in string.ascii_lowercase + string.ascii_uppercase + string.digits + "._-/"
)


def wide_authorizer(*, scopes: Iterable[str]) -> ControlPlaneTenantAuthorizer:
    """Grant ``scopes`` every tenant, every door action and every resource."""
    registry = ControlPlaneRegistry()
    entry = ScopeEntry(tenant_patterns=WIDE, action_ids=ALL_ACTIONS, resource_patterns=WIDE)
    version = register_typed_at_composition(
        registry,
        MAPPING_KEY,
        ScopeMappingArtifact(semver="1.0.0", scopes={scope: entry for scope in scopes}),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    return ControlPlaneTenantAuthorizer(
        control_plane=registry,
        scope_mapping_key=MAPPING_KEY,
        scope_mapping_version=version,
        clock=lambda: datetime.now(UTC),
    )
