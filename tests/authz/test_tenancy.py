"""The ONE tenant reader and the selection rule (D-IMPL-353 §1.3; ``SEC-002``).

Written before the module changed. What this file proves, drafted from what
would fail here:

==========================================  ==================================
Requirement                                 What would fail here
==========================================  ==================================
one reader, one field                       ``tenants_of_grant`` would read
                                            anything but ``TokenGrant.tenants``
                                            — a ``.tenant`` attribute, a claim,
                                            a header
empty means no tenant, never every tenant   an empty set would be given a
                                            tenant, or an empty-string member
                                            would count as one
the gate does not pick                      a grant spanning several tenants
                                            would have one chosen for it when
                                            the route named none
a named tenant must be granted              a path segment naming a tenant the
                                            grant does not hold would supply it
the old reader is gone                      ``tenant_of_grant`` or the
                                            ``TenantedGrant`` Protocol would be
                                            importable, and a fixture could
                                            satisfy them with a shape no token
                                            source mints (P1)
==========================================  ==================================

Every tenant name and scope string below is test vocabulary (CINV-01).
"""

from __future__ import annotations

import pytest

from ccf_runtime.authz import tenancy
from ccf_runtime.authz.tenancy import (
    AmbiguousTenantRefused,
    TenantNotGrantedRefused,
    UntenantedGrantRefused,
    acting_tenant,
    tenants_of_grant,
)
from ccf_runtime.mcp.auth import TokenGrant

A = "tenancy-a"
B = "tenancy-b"


def _grant(*tenants: str) -> TokenGrant:
    return TokenGrant(
        client_id="tenancy-caller", scopes=("s",), tenants=frozenset(tenants)
    )


class TestTheOneReader:
    def test_the_set_the_grant_carries_is_what_is_read(self) -> None:
        assert tenants_of_grant(_grant(A, B)) == frozenset({A, B})
        assert tenants_of_grant(_grant(A)) == frozenset({A})

    def test_an_empty_set_is_refused_not_defaulted(self) -> None:
        with pytest.raises(UntenantedGrantRefused, match="no tenant"):
            tenants_of_grant(_grant())

    def test_an_empty_string_member_is_refused_whole(self) -> None:
        """Refused whole, not filtered: silently narrowing a credential is a
        deployment fault hidden rather than reported."""
        with pytest.raises(UntenantedGrantRefused, match="empty"):
            tenants_of_grant(_grant(A, ""))
        with pytest.raises(UntenantedGrantRefused):
            tenants_of_grant(_grant("   "))

    def test_a_dot_tenant_subclass_is_not_a_tenanted_grant(self) -> None:
        """P1's exact shape: a subclass naming ``tenant`` while ``tenants`` is
        empty. It opened every door in the old suite; it opens nothing here."""

        class LooksTenanted(TokenGrant):
            tenant: str

        with pytest.raises(UntenantedGrantRefused):
            tenants_of_grant(
                LooksTenanted(client_id="c", scopes=("s",), tenant=A)
            )

    def test_the_old_reader_and_its_protocol_are_gone(self) -> None:
        assert not hasattr(tenancy, "tenant_of_grant")
        assert not hasattr(tenancy, "TenantedGrant")
        assert "tenant_of_grant" not in tenancy.__all__
        assert "TenantedGrant" not in tenancy.__all__


class TestTheSelectionRule:
    def test_a_named_member_is_selected(self) -> None:
        assert acting_tenant(tenants=frozenset({A, B}), named=A) == A
        assert acting_tenant(tenants=frozenset({A, B}), named=B) == B

    def test_a_named_non_member_is_refused(self) -> None:
        with pytest.raises(TenantNotGrantedRefused):
            acting_tenant(tenants=frozenset({A}), named=B)

    def test_exactly_one_and_none_named_selects_that_one(self) -> None:
        assert acting_tenant(tenants=frozenset({A}), named=None) == A

    def test_several_and_none_named_is_ambiguous_the_gate_does_not_pick(
        self,
    ) -> None:
        with pytest.raises(AmbiguousTenantRefused, match="does not pick"):
            acting_tenant(tenants=frozenset({A, B}), named=None)

    def test_an_empty_set_is_refused_here_too(self) -> None:
        """Defense in depth: ``tenants_of_grant`` refuses it first, and this
        function must not turn an empty set into an ambiguity or a match."""
        with pytest.raises(UntenantedGrantRefused):
            acting_tenant(tenants=frozenset(), named=None)
        with pytest.raises(UntenantedGrantRefused):
            acting_tenant(tenants=frozenset(), named=A)
