"""The HTTP status a governed refusal gets, by class — one table, no 500s.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §8.3 — the HTTP API as one
of the three v0 Experience Layer front doors). The ruling of record is
``D-IMPL-253`` Q18 (D-18), Dave, verbatim:

    *"1, with a modification. I agree with class-based mapping and a uniform
    body. I would not automatically classify all entitlement/fulfillment
    refusals as 409; authorization semantics may warrant 403 internally, while
    suppression-safe policy may deliberately map externally to a less revealing
    class. The response body and disclosure policy must be authoritative, not
    HTTP status. The key invariant is that no known governed refusal becomes
    500."*

and the scoping he added beside it:

    *"the exact HTTP status table remains implementation discretion while these
    are invariant: known governed refusal ≠ 500; uniform governed body;
    disclosure controls what the consumer learns."*

The three classes, and why each is the class it is
--------------------------------------------------
**400 — the request class.** *The request as posed is not acceptable.* The
fabric never reached a product because the question itself does not conform:
the class's declared contract refused it
(:class:`~ccf.products.request.ProductRequestViolation`), the payload schema
refused it (:class:`~ccf.products.payload.PayloadSchemaViolation`), or a value
in it is one the fabric may not act on
(:class:`~ccf.products.constraints.ConstraintRefusal`). This door already
answered ``400`` for its own two request-shape refusals, so a resolver's
verdict on the same request joins the family it belongs to rather than
inventing a second one.

**404 — the unavailable class.** *There is nothing here for you.*
:class:`~ccf.products.refusal.SubjectUnavailableRefusal` is the ONE outcome a
nonexistent subject and an unauthorized principal share (``D-IMPL-253`` Q27),
and it is 404 **at every disclosure level and for every internal cause**. See
the suppression note below; this row is the whole reason the table is a
function of the disclosed kind and of nothing else.

**409 — the fulfillment-withheld class.** *The question was well posed and the
fabric would not deliver an answer to it.* Every gate refusal, every peering
admission refusal, the tolerance shell, the mixing rule, the assembly
determinations, the anchor ambiguity, the policy-resolution conflict and the
mount refusal. The state of the resource — the fabric's own measured state —
conflicts with fulfilling the request, which is what ``409`` means; the shell
carries the numbers, and the status carries none of them.

Two invariants, and they are Dave's
------------------------------------
1. **No known governed refusal may become 500.** Every member of
   :data:`~ccf.products.refusal.REFUSAL_KINDS` has a row, asserted by set
   equality in ``tests/http_api/test_product_refusal_statuses.py``, and no row
   is ``5xx``. A kind added to the vocabulary without a row is RED, not a
   silent 500. ``500`` stays what it always was — the door's report that
   something reached it which is not a governed determination at all, which is
   an invariant violation and should look like one.
2. **The response body and disclosure policy are authoritative, not the
   status.** The status is a coarse routing class for an HTTP client; what a
   consumer actually *learns* is decided by
   :func:`~ccf.products.disclosure.disclose` and by nothing on this page.

Why ``subject-unavailable`` is 404 at every level
--------------------------------------------------
Q18 names it: *"authorization semantics may warrant 403 internally, while
suppression-safe policy may deliberately map externally to a less revealing
class."* An unauthorized principal is, internally, a ``403``-shaped fact — and
answering ``403`` would tell that principal the subject exists, which is the
leak ``D-IMPL-253`` amendment 2 (4) names first in its list of six channels.
So the mapping is taken from the **disclosed kind** and never from the internal
cause: the two causes share one kind, so they share one status, and no branch
exists here that could take the cause into account even if a later edit wanted
to.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ccf.agents.errors import AssemblyRefusal
from ccf.contracts.base import CCFContract
from ccf.graph.product_source import ProductMountRefusal
from ccf.peering.admission import (
    AdmissionRefusal,
    ContractRefusal,
    LineageContinuityRefusal,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
)
from ccf.products.composite import ChildAdmissionRefusal
from ccf.products.composition import MixingRefusal
from ccf.products.constraints import ConstraintRefusal, PolicyResolutionConflict
from ccf.products.gates import (
    TTLAnchorRefusal,
    AttestationRefusal,
    DependencyInvalidationRefusal,
    DeclaredObligationRefusal,
    EmptyOperatorRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    ProductInvariantRefusal,
    ToleranceExceededRefusal,
    TTLRefusal,
)
from ccf.products.payload import PayloadSchemaViolation
from ccf.products.refusal import REFUSAL_KINDS, SubjectUnavailableRefusal
from ccf.products.request import AnchorAmbiguityRefusal, ProductRequestViolation

__ccf_mode__ = "algorithmic"

__all__ = [
    "STATUS_BY_KIND",
    "STATUS_FULFILLMENT_WITHHELD",
    "STATUS_REQUEST",
    "STATUS_UNAVAILABLE",
    "status_for",
]


#: The request class: the request as posed is not acceptable.
STATUS_REQUEST: Final[int] = 400

#: The unavailable class: suppression-safe, and the internal cause is never on
#: the status (``D-IMPL-253`` Q27 with amendment 2 (4)).
STATUS_UNAVAILABLE: Final[int] = 404

#: The fulfillment-withheld class: the fabric could not construct or deliver.
STATUS_FULFILLMENT_WITHHELD: Final[int] = 409


#: The table, **keyed by refusal class** rather than by token.
#:
#: Keyed by class deliberately, and it is not a style choice: a table of kind
#: *strings* would be a second spelling of a vocabulary
#: :data:`~ccf.products.refusal.REFUSAL_KINDS` already owns, and the two would
#: agree on the day they were written and drift on the first rename. Keyed by
#: class, a renamed token moves both sides at once and a *deleted* class is an
#: ``ImportError`` rather than an orphaned row.
_STATUS_BY_TYPE: Final[Mapping[type[CCFContract], int]] = MappingProxyType(
    {
        # -- the request class ------------------------------------------------
        ProductRequestViolation: STATUS_REQUEST,
        PayloadSchemaViolation: STATUS_REQUEST,
        ConstraintRefusal: STATUS_REQUEST,
        # -- the unavailable class --------------------------------------------
        SubjectUnavailableRefusal: STATUS_UNAVAILABLE,
        # -- the fulfillment-withheld class -----------------------------------
        GateRefusal: STATUS_FULFILLMENT_WITHHELD,
        EmptyOperatorRefusal: STATUS_FULFILLMENT_WITHHELD,
        LineageMismatchRefusal: STATUS_FULFILLMENT_WITHHELD,
        LineageAttributionRefusal: STATUS_FULFILLMENT_WITHHELD,
        TTLRefusal: STATUS_FULFILLMENT_WITHHELD,
        TTLAnchorRefusal: STATUS_FULFILLMENT_WITHHELD,
        # `D-IMPL-334`: the world moved under a product this fabric holds —
        # the fabric's own measured state conflicts with fulfilling a
        # well-posed request. A gate-family refusal, the class rule above.
        DependencyInvalidationRefusal: STATUS_FULFILLMENT_WITHHELD,
        # `D-IMPL-336`: a child offered to a composition did not pass
        # admission — the composite analog of the peering `admission-refusal`
        # row below. A 400 would blame a caller who asked correctly; a 404
        # would claim an absence that is not the case.
        ChildAdmissionRefusal: STATUS_FULFILLMENT_WITHHELD,
        AttestationRefusal: STATUS_FULFILLMENT_WITHHELD,
        DeclaredObligationRefusal: STATUS_FULFILLMENT_WITHHELD,
        # `24.10-02` / `R-11`: a deployment's own declared product invariant
        # refused. The reason it belongs in this class is the reason
        # `declared-obligation-refusal` does, and it is stated rather than
        # inherited by copying the number: the fabric CONSTRUCTED the product
        # — the universal gates admitted it — and then withheld it because
        # something the class declared about itself did not hold. That is a
        # fulfillment fact about the answer, not a fault in the question (the
        # request was well-formed and answerable) and not a statement that the
        # subject does not exist. A `400` would blame a caller who asked
        # correctly; a `404` would claim an absence that is not the case.
        ProductInvariantRefusal: STATUS_FULFILLMENT_WITHHELD,
        ToleranceExceededRefusal: STATUS_FULFILLMENT_WITHHELD,
        MixingRefusal: STATUS_FULFILLMENT_WITHHELD,
        AssemblyRefusal: STATUS_FULFILLMENT_WITHHELD,
        AnchorAmbiguityRefusal: STATUS_FULFILLMENT_WITHHELD,
        PolicyResolutionConflict: STATUS_FULFILLMENT_WITHHELD,
        AdmissionRefusal: STATUS_FULFILLMENT_WITHHELD,
        PayloadTooLargeRefusal: STATUS_FULFILLMENT_WITHHELD,
        SignatureRefusal: STATUS_FULFILLMENT_WITHHELD,
        ContractRefusal: STATUS_FULFILLMENT_WITHHELD,
        PolicyBindingRefusal: STATUS_FULFILLMENT_WITHHELD,
        LineageContinuityRefusal: STATUS_FULFILLMENT_WITHHELD,
        ProductMountRefusal: STATUS_FULFILLMENT_WITHHELD,
    }
)


#: What a door renders: the disclosed kind's status class.
#:
#: Derived from :data:`_STATUS_BY_TYPE` through
#: :data:`~ccf.products.refusal.REFUSAL_KINDS`, so no kind token is spelled in
#: this module at all. Closed by set equality against the vocabulary in
#: ``tests/http_api/test_product_refusal_statuses.py``: a kind added to
#: ``REFUSAL_KINDS`` without a row here is a red test, which is the whole
#: mechanism behind *"no known governed refusal becomes 500"*.
STATUS_BY_KIND: Final[Mapping[str, int]] = MappingProxyType(
    {
        REFUSAL_KINDS[refusal_type]: status
        for refusal_type, status in _STATUS_BY_TYPE.items()
    }
)


def status_for(kind: str) -> int:
    """The status class for one **disclosed** refusal kind.

    A function of the kind and of nothing else — not of the internal cause, not
    of the disclosure level, not of the principal. That is what makes the
    suppression property structural: there is no argument here that could carry
    the difference between *you may not* and *there is no such thing*.

    Args:
        kind: :attr:`~ccf.products.refusal.RefusalEnvelope.kind`, as the door
            received it.

    Returns:
        One of :data:`STATUS_REQUEST`, :data:`STATUS_UNAVAILABLE` or
        :data:`STATUS_FULFILLMENT_WITHHELD`.

    Raises:
        KeyError: ``kind`` is not in the vocabulary. Deliberately not a
            default: a token this table does not hold is not a governed refusal
            this SDK minted, and answering it with a plausible status would be
            the door inventing a contract. A caller that must not raise asks
            ``kind in STATUS_BY_KIND`` first — which is what the product route
            does, so an unknown token falls through to
            :func:`~ccf.products.door.served_answer` and reaches the client as
            the opaque door fault it is.
    """
    return STATUS_BY_KIND[kind]
