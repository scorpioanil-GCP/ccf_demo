# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The gate decides on the grant shape a DEPLOYMENT actually mints.

Found by the Tier-1 close panel (Codex), reproduced before repair. Lane HTTP
built the gate against `grant.tenant` — a singular string — while Lane MCP
shipped `TokenGrant.tenants`, a `frozenset`. Two spellings of one concept, one
per lane, neither wrong on its own.

The consequence was not a style defect. `tenant_of_grant` read `.tenant`, which
the shipped contract does not have, so **every authenticated request in any real
deployment refused with `untenanted-grant`** — while `tests/http_api` stayed
green, because its fixture minted a test-only `TenantedTokenGrant` subclass that
added the missing attribute. The suite was measuring a shape production never
produces.

It failed CLOSED, so nothing was exposed. What was broken is the feature.
"""

from __future__ import annotations

import pytest

from ccf_runtime.authz.tenancy import UntenantedGrantRefused, tenants_of_grant
from ccf_runtime.mcp.auth import TokenGrant


def test_the_shipped_contract_is_what_the_gate_reads() -> None:
    """The regression in one line: a grant a token source really mints."""
    grant = TokenGrant(
        client_id="c", scopes=("s",), tenants=frozenset({"acme-bank"})
    )
    assert tenants_of_grant(grant) == frozenset({"acme-bank"})


def test_a_grant_naming_no_tenant_is_refused() -> None:
    grant = TokenGrant(client_id="c", scopes=("s",))
    with pytest.raises(UntenantedGrantRefused):
        tenants_of_grant(grant)


def test_an_empty_tenant_name_is_not_a_tenant() -> None:
    """MCP's `granted_tenants` accepted any string including `""`; the HTTP
    side rejected it. The asymmetry is closed here, at the shared reader."""
    grant = TokenGrant(client_id="c", scopes=("s",), tenants=frozenset({""}))
    with pytest.raises(UntenantedGrantRefused):
        tenants_of_grant(grant)


def test_a_non_grant_object_is_refused() -> None:
    class Impostor:
        tenants = frozenset({"acme-bank"})

    with pytest.raises(UntenantedGrantRefused):
        tenants_of_grant(Impostor())
