"""The ONE source of the tenants a request may act under: the verified grant.

SDK-defined (CLAUDE.md §8.2/§8.3; ``SEC-002``; D-IMPL-353 §1.3). Before this
module the tenant a door authorized against arrived from whatever the caller
happened to put in a path segment, a query parameter or a request body, and
the authorizer then faithfully decided about the tenant the caller had named.
That is not an authorization decision; it is a decision the caller writes half
of.

**One reader, over one field.** :func:`tenants_of_grant` reads
:attr:`~ccf_runtime.mcp.auth.TokenGrant.tenants` — the set a deployment's token
source minted — and nothing else reads a tenant off a credential anywhere in
the tree. There is no ``.tenant`` scalar, no Protocol a subclass could satisfy
by adding one, and therefore no shape a test fixture can mint that a
deployment's token source cannot (the P1 defect: a suite that stayed green
while the HTTP door refused every real credential, because its fixture
subclassed the grant to carry a field production never minted).

**A decision is about one tenant, so the gate SELECTS one from the set** —
:func:`acting_tenant`, and the rule has three arms and no fourth:

* the route names a tenant (a path segment) → it must be a member of the
  grant's set, else refuse;
* the route names none and the grant holds exactly one → that one;
* the route names none and the grant holds several → **refuse as ambiguous;
  the gate does not pick.** A gate that chose would be writing half of the
  decision itself, which is the ``SEC-002`` defect moved server-side.

A path segment may therefore **assert** a tenant — the segment is part of a
product's address and a URI has to keep meaning what it meant — and may never
**supply** one the credential does not hold.

**Why the readers fail closed rather than defaulting.** A grant carrying no
tenant is a deployment that has not said who its credentials belong to, and the
only two things a door could do with one are *refuse* and *pick a tenant for
it*. The second is the ``SEC-002`` defect wearing a server-side hat, so every
refusal here is raised, typed, and rendered by the gate as a refusal. None of
them is provokable by a caller — a caller cannot change which tenants its
credential names — so refusing discloses nothing and opens no oracle.

Tenant names are deployment vocabulary; this module holds none (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "AmbiguousTenantRefused",
    "TenantNotGrantedRefused",
    "UntenantedGrantRefused",
    "acting_tenant",
    "tenants_of_grant",
]


class UntenantedGrantRefused(RuntimeError):
    """The verified grant names no tenant, so no door can act on one.

    A *deployment* fault rather than a caller fault: the token source decides
    what a grant carries, and a caller has no way to add a tenant to its own
    credential. Raised rather than returned as an empty set because every
    caller of :func:`tenants_of_grant` needs a tenant to proceed at all, and an
    empty return is an invitation to a ``or "default"`` somewhere downstream —
    which is exactly the value this module exists to refuse.
    """


class AmbiguousTenantRefused(RuntimeError):
    """The grant spans several tenants and the route named none.

    The gate does not pick (D-IMPL-353 §1.3). An operator credential that
    legitimately spans tenants reaches a tenant-less route by presenting a
    credential scoped to one, or by addressing a route that names the tenant;
    the SDK will not choose on its behalf.
    """


class TenantNotGrantedRefused(RuntimeError):
    """The route named a tenant the grant does not hold.

    A path segment may agree with the credential; it may never supply a tenant
    the credential lacks. Rendered by the gate as its one constant denial, so a
    caller cannot use it to learn which tenants it is near.
    """


def tenants_of_grant(grant: object) -> frozenset[str]:
    """The tenants ``grant`` may act for — the single read, or refuse.

    Args:
        grant: The **verified** grant a bound auth hook produced. Unverified
            input never reaches here: the gate refuses 401 before it asks.
            Typed ``object`` deliberately and narrowed here: the reader must
            not trust an annotation, because a deployment's hook is its own
            code, and the one thing this function must never do is read a
            ``tenants`` attribute off something that is not the shipped
            contract.

    Returns:
        The non-empty set of tenants every downstream selection is made from.

    Raises:
        UntenantedGrantRefused: ``grant`` is not a
            :class:`~ccf_runtime.mcp.auth.TokenGrant`, or its set is empty,
            or any member is not a non-empty string. All are the same fact
            from a door's point of view — there is no tenant to act under —
            and all refuse rather than inventing one. A set with one empty
            member is refused **whole**: filtering it would silently narrow a
            credential, which hides a deployment fault instead of reporting
            it.
    """
    if not isinstance(grant, TokenGrant):
        raise UntenantedGrantRefused(
            "the object presented as the verified grant is not a TokenGrant,"
            " so it carries no tenants this reader will read; the one reader"
            " reads the one field of the one contract a token source mints"
            " (SEC-002; D-IMPL-353 §1.3)"
        )
    tenants = grant.tenants
    if not isinstance(tenants, frozenset) or not tenants:
        raise UntenantedGrantRefused(
            "the verified grant names no tenant, so there is no tenant for"
            " this request to act under. The tenant is the grant's `tenants`"
            " set and only that: a door that read it from the path, the query"
            " string, the body, or any other attribute of the credential would"
            " let the caller — or a fixture — write half of its own"
            " authorization decision (SEC-002; D-IMPL-353 §1.3). Mint"
            " credentials that carry `tenants`"
        )
    if any(not isinstance(name, str) or not name.strip() for name in tenants):
        raise UntenantedGrantRefused(
            "the verified grant's `tenants` set carries an empty tenant name;"
            " an empty name is not a tenant, and the set is refused whole"
            " rather than silently narrowed (SEC-002; D-IMPL-353 §1.3)"
        )
    return tenants


def acting_tenant(*, tenants: frozenset[str], named: str | None) -> str:
    """Select the one tenant this request acts under, or refuse.

    Args:
        tenants: What :func:`tenants_of_grant` returned.
        named: The tenant the route itself named — a path segment — or
            ``None`` when the route's template carries none. Never a value read
            from the query string or the body: those are not sources.

    Returns:
        The one tenant the authorizer is asked about and the capability is
        minted for.

    Raises:
        UntenantedGrantRefused: ``tenants`` is empty. Refused here too, so this
            function cannot turn an empty set into a match or an ambiguity.
        TenantNotGrantedRefused: ``named`` is not a member of ``tenants``.
        AmbiguousTenantRefused: nothing was named and ``tenants`` holds more
            than one. The gate does not pick.
    """
    if not tenants:
        raise UntenantedGrantRefused(
            "no tenant can be selected from an empty set (SEC-002)"
        )
    if named is not None:
        if named not in tenants:
            raise TenantNotGrantedRefused(
                "the route names a tenant the verified grant does not hold; a"
                " path segment may agree with the credential and may never"
                " supply a tenant it lacks (SEC-002; D-IMPL-353 §1.3)"
            )
        return named
    if len(tenants) == 1:
        return next(iter(tenants))
    raise AmbiguousTenantRefused(
        "the verified grant spans several tenants and this route names none,"
        " so there is no one tenant to decide about; the gate does not pick."
        " Present a credential scoped to one tenant, or address a route that"
        " names the tenant in its path (D-IMPL-353 §1.3)"
    )
