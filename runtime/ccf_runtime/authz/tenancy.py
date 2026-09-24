"""The ONE source of the tenant a request acts under: the verified grant.

SDK-defined (CLAUDE.md §8.2/§8.3; ``SEC-002``). Before this module the tenant
a door authorized against arrived from whatever the caller happened to put in
a path segment, a query parameter or a request body, and the authorizer then
faithfully decided about the tenant the caller had named. That is not an
authorization decision; it is a decision the caller writes half of.

**The rule, and it has no second clause.** ``tenant := grant.tenant``. A path
segment may **assert equality** with the verified grant's tenant — the segment
is part of a product's address and a URI has to keep meaning what it meant —
but it may never **supply** the value. Nothing else is a source: not a body
field, not a query parameter, not a header.

**Why the reader fails closed rather than defaulting.** A grant carrying no
tenant is a deployment that has not said who its credentials belong to, and
the only two things a door could do with one are *refuse* and *pick a tenant
for it*. The second is the ``SEC-002`` defect wearing a server-side hat, so
this raises :class:`UntenantedGrantRefused` and the gate renders it as a
refusal. It is deliberately **not** provokable by a caller — a caller cannot
change which tenant its credential names — so refusing discloses nothing and
opens no oracle.

Tenant names are deployment vocabulary; this module holds none (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__ccf_mode__ = "algorithmic"

__all__ = ["TenantedGrant", "UntenantedGrantRefused", "tenant_of_grant"]


class UntenantedGrantRefused(RuntimeError):
    """The verified grant names no tenant, so no door can act on one.

    A *deployment* fault rather than a caller fault: the token source decides
    what a grant carries, and a caller has no way to add a tenant to its own
    credential. Raised rather than returned as ``None`` because every caller
    of :func:`tenant_of_grant` needs a tenant to proceed at all, and an
    ``Optional`` return is an invitation to a ``or "default"`` somewhere
    downstream — which is exactly the value this module exists to refuse.
    """


@runtime_checkable
class TenantedGrant(Protocol):
    """A verified credential that names the tenant it acts for.

    Protocol rather than a concrete type (CLAUDE.md §11): which credential
    class a deployment's token source mints is its own statement, and this
    package has business only with the one attribute it authorizes against.
    """

    tenant: str


def tenant_of_grant(grant: object) -> str:
    """The tenant ``grant`` names, or refuse.

    Args:
        grant: The **verified** grant a bound auth hook produced. Unverified
            input never reaches here: the gate refuses 401 before it asks.

    Returns:
        The tenant every downstream authorization decision is made under.

    Raises:
        UntenantedGrantRefused: the grant carries no ``tenant``, or carries
            one that is not a non-empty string. Both are the same fact from a
            door's point of view — there is no tenant to act under — and both
            refuse rather than inventing one.
    """
    tenant = getattr(grant, "tenant", None)
    if isinstance(tenant, str) and tenant:
        return tenant
    raise UntenantedGrantRefused(
        "the verified grant names no tenant, so there is no tenant for this"
        " request to act under. The tenant is the grant's and only the"
        " grant's: a door that read it from the path, the query string or the"
        " body would let the caller write half of its own authorization"
        " decision (SEC-002). Mint credentials that carry a tenant"
    )
