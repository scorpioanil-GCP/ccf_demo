"""What a question came back with — the answer, or the governed "no".

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§4 (``D-07`` … ``D-10``). The whitepaper specifies the Context Product Contract
(§6.3) and the three validation gates that refuse a candidate (§7.6); it does
not specify a *client's* reading of either, because it does not commit to a
transport. This module is that reading.

A refusal is a value
--------------------
A refusal is the fabric **working**: the gates ran and the governed answer was
"no, and here is why". So :class:`Result` carries either half, and a caller
branches on :attr:`Result.refused` (``D-07``). The contract spoke in both
cases, which is why neither case is an exception.

The assembly boundary is the rule that decides which fields survive
-------------------------------------------------------------------
``D-09``. Everything that existed **before** assembly stays readable on a
refused result — the request identity, the refusal's reason, key and kind, and
whatever pre-assembly lineage the refusal itself carries. Everything that only
exists **after** a successful assembly is absent, and reading it raises
(``D-08``). The two groups are named in :data:`PRE_ASSEMBLY_FIELDS` and
:data:`GUARDED_FIELDS`, and ``tests/client/test_result_guard.py`` asserts the
two partition this class's public properties exactly — so a seventh property
cannot appear next year on neither side of the boundary.

The inversion, stated once
--------------------------
**The exception does not fire when the fabric says no. It fires when the caller
ignores the fabric saying no.** A silent ``None`` in place of a payload is how a
governed refusal becomes an empty answer three layers downstream, at a point
where nothing can tell the difference between "no companies matched" and "the
question was never answered".

The accepted trade-off, recorded so nobody re-derives it
--------------------------------------------------------
A single :class:`Result` type means ``mypy`` cannot statically prove the caller
checked :attr:`~Result.refused`; the guard is runtime-only. That is the right
trade for a client SDK whose first audience is a reader — a served/refused
union would make the type system happy and the two-line example unreadable.
**Do not split the type to satisfy the typechecker**; it is a ruled decision,
not an oversight.

Why this class is not a Pydantic contract
------------------------------------------
Every other public shape in this package derives from
:class:`~ccf.contracts.base.CCFContract`, and this one deliberately does not.
The guard requires attribute access to be a *computation*, and a Pydantic field
is a *value*: a declared ``payload`` field would be readable as ``None`` on a
refused result before any code of this module's ran, which is the exact defect
``D-08`` forbids. Validation is not deferred by that choice — the boundary this
type sits behind is :class:`~ccf.client.wire.WireOutcome`, which is a frozen
``extra=forbid`` contract, and the vessel it carries is re-parsed as a
:class:`~ccf.products.contract.ContextProductContract` before it reaches here.

This module is algorithmic (CINV-03): typed values and pure guards, no I/O, no
clock, no LLM dependency ever.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from ccf.client.errors import RefusedResultError
from ccf.halflife.assessment import DebtAssessment
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.refusal import RefusalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = ["GUARDED_FIELDS", "PRE_ASSEMBLY_FIELDS", "Refusal", "Result"]


#: The client's name for the one canonical refusal envelope.
#:
#: Deliberately the *same type* rather than a client-side copy of it. A parallel
#: shape with the same members would need a gate asserting the two agree, and
#: that gate would be asserting that a rename is still a rename — while the day
#: it drifted, a client's ``refusal.kind`` would name a vocabulary the fabric no
#: longer speaks. ``D-28``'s envelope already *is* the client-facing reading:
#: it promotes ``reason``, ``key`` and ``detail``, carries ``kind`` unflattened,
#: and attaches the pre-assembly request identity and lineage that ``D-09``
#: requires. There is nothing left for a second type to add.
#:
#: It is not a fifth exported name: ``D-03``'s four names are the *package's*
#: surface, and the spec's own words put this one on the third — ``Result``
#: (*with its* ``Refusal``). A reader reaches it through ``result.refusal``.
Refusal = RefusalEnvelope


#: The six fields that exist only after a successful assembly, and which a
#: refused :class:`Result` therefore refuses to hand over (``D-08``).
#:
#: Read by the guard itself — :meth:`Result._served_or_raise` enumerates this
#: tuple in the message it raises — and by every assertion in
#: ``tests/client/test_result_guard.py``, so the two cannot drift into
#: disagreeing about what is guarded.
#:
#: **Why each is here**, from ``17-RESEARCH.md`` §3.3: ``payload``, ``debt``,
#: ``lineage`` and ``expires_at`` are members of a vessel that does not exist
#: until assembly succeeded; ``content_address`` is a function of the whole
#: vessel and so exists only once the vessel does; and ``replay_ref`` exists
#: only after the replay record was written, which is strictly after all three
#: gates passed.
GUARDED_FIELDS: Final[tuple[str, ...]] = (
    "payload",
    "debt",
    "content_address",
    "replay_ref",
    "lineage",
    "expires_at",
)

#: The fields that existed **before** assembly and are readable on either half
#: (``D-09``), so a refusal stays auditable: the branch itself, the refusal, and
#: the request identity that was refused.
#:
#: The pre-assembly *lineage* is not among them because it rides on the refusal
#: — ``result.refusal.pre_assembly_lineage`` — where the distinction between
#: *there was none* and *it was dropped* is already carried. Restating it here
#: would give a served result a member with no true value.
PRE_ASSEMBLY_FIELDS: Final[tuple[str, ...]] = (
    "refused",
    "refusal",
    "product_id",
    "parameters",
    "temporal_boundary",
)


@dataclass(frozen=True, slots=True)
class _Served:
    """The post-assembly half, bundled so it is present or absent as a unit.

    Private, and a bundle rather than three optional attributes on
    :class:`Result`, for one reason: with three optionals a guard has to be
    written — and remembered — once per field, and the typechecker cannot
    narrow any of them from ``self._refusal is None``. One optional bundle
    makes "the vessel exists" a single fact, and every guarded property reads
    it through the one function that checks that fact.
    """

    vessel: ContextProductContract
    content_address: str
    replay_ref: str | None


class Result:
    """The answer or the refusal — and the contract spoke in either case.

    ``D-07`` … ``D-09``. Constructed in **exactly one place**, the decoder
    inside :class:`~ccf.client.client.ProductClient` (``D-12``), which is what
    makes "every transport returns the same shape" a code path an adapter
    cannot avoid rather than a convention it is asked to follow.
    ``tests/client/test_surface.py`` asserts that one-site property with an AST
    scan over ``src/``, ``runtime/`` and ``examples/``.

    Read it the way the two-line example does::

        if result.refused:
            log(result.refusal.reason, result.refusal.key)
        else:
            use(result.payload)

    Args:
        product_id: The product class the question addressed.
        parameters: What the caller supplied. An empty mapping is a question
            that needed nothing beyond its axes — a positive statement, not a
            missing value.
        temporal_boundary: The instant the caller asked against, or ``None``
            for *the server's decision instant* — the rule documented on
            :meth:`~ccf.client.client.ProductClient.ask`.
        vessel: The served product, or ``None`` on a refusal.
        content_address: The vessel's address. Required alongside a vessel and
            forbidden alongside a refusal, on the same reasoning
            :class:`~ccf.client.wire.WireOutcome` records: a refusal is a
            governed answer, not a content-addressed artifact.
        replay_ref: The replay record's reference, when the producer emitted
            one. ``None`` on a served result is *the producer published none*,
            which is a fact about that deployment rather than about this
            result.
        refusal: The governed "no", or ``None`` on a served result.

    Raises:
        ValueError: the result carries both halves or neither, or a content
            address disagrees with which half it carries. Enforced at
            construction rather than documented, because three states would
            mean every consumer writes its own answer to "what does neither
            mean" and they would not all write the same one.
    """

    __slots__ = ("_parameters", "_product_id", "_refusal", "_served", "_temporal")

    def __init__(
        self,
        *,
        product_id: str,
        parameters: Mapping[str, Any],
        temporal_boundary: datetime | None,
        vessel: ContextProductContract | None,
        content_address: str | None,
        replay_ref: str | None,
        refusal: Refusal | None,
    ) -> None:
        if vessel is not None and refusal is not None:
            raise ValueError(
                "a `Result` carries a served product or a refusal, never both"
                " — one governed answer cannot be two"
            )
        if vessel is None and refusal is None:
            raise ValueError(
                "a `Result` carries a served product or a refusal, and this one"
                " carries neither — a transport that produced no answer raises"
                " `TransportError` instead of yielding an empty result"
            )
        if refusal is not None and content_address is not None:
            raise ValueError(
                "a refused `Result` carries no content address — a refusal is a"
                " governed answer, not a content-addressed artifact"
            )

        self._product_id = product_id
        self._parameters = parameters
        self._temporal = temporal_boundary
        self._refusal = refusal
        self._served: _Served | None = None
        if vessel is not None:
            # Checked here rather than beside the other two so the narrowing is
            # the typechecker's as well as the reader's: below this line
            # `content_address` is a `str`, with no cast and no sentinel.
            if not content_address:
                raise ValueError(
                    "a served `Result` carries the vessel's content address; it"
                    " is the whole reason a consumer can check that the bytes"
                    " it holds are the ones the producer addressed"
                )
            self._served = _Served(
                vessel=vessel,
                content_address=content_address,
                replay_ref=replay_ref,
            )

    # ------------------------------------------------------------------
    # Pre-assembly — readable on either half (D-09)
    # ------------------------------------------------------------------

    @property
    def refused(self) -> bool:
        """``True`` when the fabric answered "no", ``False`` when it answered.

        The branch, and the only member a caller is obliged to read first.
        Readable on both halves without raising, because a guard on the branch
        itself would make the guard unreachable.
        """
        return self._refusal is not None

    @property
    def refusal(self) -> Refusal | None:
        """The governed "no" and everything it was about, or ``None``.

        Carries ``kind`` unflattened, the promoted ``reason``, ``key`` and
        ``detail``, every remaining field the refusal type declared, the
        pre-assembly request identity and the pre-assembly lineage — so the
        "no" stays auditable at the seam (``D-09``, ``D-28``).
        """
        return self._refusal

    @property
    def product_id(self) -> str:
        """The product class the question addressed."""
        return self._product_id

    @property
    def parameters(self) -> Mapping[str, Any]:
        """What the caller asked with, echoed back and cross-checked in transit."""
        return self._parameters

    @property
    def temporal_boundary(self) -> datetime | None:
        """The instant asked against, or ``None`` for the server's own."""
        return self._temporal

    # ------------------------------------------------------------------
    # Post-assembly — guarded, one property per name in GUARDED_FIELDS
    # ------------------------------------------------------------------

    def _served_or_raise(self, field: str) -> _Served:
        """The post-assembly half, or the refusal that says there isn't one.

        The guard. It reads :data:`GUARDED_FIELDS` so that the message names
        every field a caller must branch before reading, which keeps the
        enumeration a reader sees and the enumeration the tests assert over the
        same one tuple.
        """
        served = self._served
        if served is not None:
            return served
        reason = self._refusal.reason if self._refusal is not None else "unknown"
        raise RefusedResultError(
            f"`{field}` is a post-assembly field and this result was refused"
            f" — the fabric answered `{reason}`, so no product was assembled and"
            f" there is no `{field}` to read. Branch on `result.refused` before"
            f" reading any of: {', '.join(GUARDED_FIELDS)}. The refusal itself"
            " is on `result.refusal`"
        )

    @property
    def payload(self) -> Mapping[str, Any]:
        """The typed answer the product class declares."""
        return self._served_or_raise("payload").vessel.payload

    @property
    def debt(self) -> DebtAssessment | None:
        """The measured Context Debt in force when the product was assembled.

        ``None`` is the vessel's own positive assertion *this product was
        assembled with no debt assessment* (whitepaper §7.7), and is a fact
        about the producing deployment rather than about this result.
        """
        return self._served_or_raise("debt").vessel.debt

    @property
    def content_address(self) -> str:
        """The vessel's address, recomputed from its bytes on arrival.

        Never the value the wire claimed: the recomputation happens on the one
        decode path (:func:`ccf.client.codec.verify_content_address`), and a
        wire that disagrees with its own bytes is a
        :class:`~ccf.client.errors.TransportError` rather than a result.
        """
        return self._served_or_raise("content_address").content_address

    @property
    def replay_ref(self) -> str | None:
        """The replay record this decision was written into, when there is one."""
        return self._served_or_raise("replay_ref").replay_ref

    @property
    def lineage(self) -> ProductLineage:
        """The post-assembly L axis — operators invoked, policy versions, anchor."""
        return self._served_or_raise("lineage").vessel.lineage

    @property
    def expires_at(self) -> datetime:
        """When this answer stops being one, per its class's TTL ceiling."""
        return self._served_or_raise("expires_at").vessel.expires_at

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """A one-line reading that never touches a guarded field.

        Deliberately says which half it is and nothing about the payload: a
        repr that dereferenced the vessel would raise from inside a debugger on
        exactly the results a developer is debugging.
        """
        if self._refusal is not None:
            return (
                f"Result(product_id={self._product_id!r}, refused=True,"
                f" reason={self._refusal.reason!r})"
            )
        return f"Result(product_id={self._product_id!r}, refused=False)"
