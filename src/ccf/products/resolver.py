"""The seam that yields a *gate-admitted* product, declared in ``src/``.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). The whitepaper
specifies the Context Product Contract (§6.3), the three validation gates
(§7.6) and the Decision Replay record (§7.10); it specifies no client, and so
no seam through which a client reaches a served product. The ruling of record
is ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` **Amendment 1
§B** (Dave, 2026-08-15): *the resolver Protocol is declared in* ``src/``, *and
the SDK ships its reference implementation in* ``src/`` *as well*.

Why the ruling was needed
-------------------------
Phase 17 research measured that **no** ``src/``-resident seam yields a
gate-admitted product, and that **no** module under ``src/`` imports
``ccf_runtime``. The two seams that do yield one live in ``runtime/``, behind
the two MCP doors. The nearest ``src/`` seam,
:class:`~ccf.agents.assembler.ContextAssemblerProtocol`, sits one level *below*
the vessel: its :class:`~ccf.agents.assembler.AssemblyOutcome` carries a
payload, and no contract, no gates and no replay record. A client had no
implementable path.

That gap has a second face. The SDK ships every *part* of assemble → gate →
serve — :func:`~ccf.products.gates.run_gates` and
:func:`~ccf.replay.serve.serve` are both ``src/``-resident — and has never
shipped the *composition*, so every deployment writes it. The rejected first
example wrote it in front of a reader who wanted to ask one question. **The
missing resolver and the oversized example are the same defect seen from two
directions**, which is why :class:`GovernedResolver` ships here rather than
being described in a guide.

The two widenings, and the measured reason for each
---------------------------------------------------
This seam's five arguments are copied from
:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` **exactly** — same
names, same order, same keyword-only discipline, same nullability — so a
deployment that already wrote a resolver for a door recognises the signature on
sight and maintains one shape rather than two. Only the *return type* widens,
in the two ways research measured to be missing:

**DIV-2 — a replay reference.** The seam returns
:class:`~ccf.replay.serve.ServedProduct`, not
:class:`~ccf.products.gates.ServableProduct`. The first carries ``product``
*and* ``replay_ref``; the second carries only the product.
:mod:`ccf.replay.serve` records the measurement plainly in its own docstring:
all three shipped delivery paths serialize the servable's product and **none**
of them reads its replay reference. The seam being typed to the narrower vessel
is precisely why no door can reach a replay reference. The ruled client
``Result`` exposes one, so the seam must carry one.

**DIV-4 — a refusal.** Every refusal the fabric produces behind the current
seam has nowhere to go: the seam admits no refusal in its union, so a
``GateRefusal`` or a request-conformity verdict either becomes an exception or
becomes silence. :class:`~ccf.products.refusal.RefusalEnvelope` is where it
goes, and :data:`ResolverOutcome` is the union that carries it.

A named divergence, recorded rather than left to be discovered
--------------------------------------------------------------
**The two** ``runtime/`` **seams are unchanged by this module**, and both
remain typed to the narrower vessel:
:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` and
:class:`~ccf_runtime.mcp.experience.ExperienceProductResolverProtocol`. So
there are, for now, two return shapes across three seams. Unifying them is not
in scope for this phase, is not ruled, and would be a door's worth of work;
stating the divergence here is what keeps it a known cost rather than a
surprise for whoever reads the three seams side by side.

Dependency direction
--------------------
This module lives in :mod:`ccf.products`, beside :mod:`ccf.products.gates` and
:mod:`ccf.products.request`, because it is **product machinery a client
consumes** rather than client machinery. The edge therefore runs one way:
``ccf.client`` depends on ``ccf.products``, never the reverse. A resolver
importing the client would make the fabric's product surface conditional on a
delivery surface, which is the inversion CLAUDE.md §10 keeps out of the layer
stack.

No boundary is crossed to achieve any of this: nothing imported below leaves
``ccf``. ``tests/invariants/test_src_does_not_import_runtime.py`` asserts that
for the whole tree rather than for this module's good intentions.

This module is algorithmic (CINV-03): no LLM client on this path, ever. The
gate sequence and the replay append are the algorithmic half of the
Algorithmic ⇄ Semantic Alternation (whitepaper §7.6.6), and a model call
anywhere in the composition would put an unrecorded, irreproducible step
between a candidate and its content address.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct

__ccf_mode__ = "algorithmic"

__all__ = [
    "ProductNotResolvable",
    "ResolverOutcome",
    "ServedProductResolverProtocol",
]


#: What a resolver returns: a served product, or the refusal that stands
#: instead of one.
#:
#: A **named** alias rather than an inline union, so the two halves are one
#: nameable thing a ``match`` statement, a decoder and a docstring can all
#: spell identically. An inline union spelled at each of those sites is three
#: places to add a third member to, and the client's decoder is required to be
#: total over exactly this set.
#:
#: Both halves are frozen, ``extra=forbid`` contracts, so an outcome is a value
#: the caller carries onward — it holds no handle, no session and no callback,
#: which is what lets the same shape cross an in-process call and a wire.
ResolverOutcome = ServedProduct | RefusalEnvelope


class ProductNotResolvable(LookupError):
    """The resolver holds no product at the address it was called with.

    An **absence**, so a ``LookupError``, in the voice
    :class:`~ccf_runtime.mcp.egress.ProductNotServable` already uses at the
    egress door. Deliberately a distinct type rather than that one: importing
    it would be the first ``src`` → ``runtime`` edge in the tree, which is
    exactly what Amendment 1 §B ruled out. The two are siblings by shape, not
    by inheritance, and neither is reachable from the other's tree.

    **Raised, never returned**, and the distinction is the one
    :class:`~ccf.products.request.ProductRequestViolation` draws for itself: a
    question this class does not answer is a *bad question* and comes back as a
    refusal value, while an address this resolver was never wired to serve is a
    *broken deployment* and comes back as an exception. Reporting the two the
    same way would let a mis-wiring read to a caller as a governed "no".
    """


@runtime_checkable
class ServedProductResolverProtocol(Protocol):
    """What a deployment plugs into an in-process delivery surface.

    A Protocol rather than a base class (CLAUDE.md §11), for the reason
    :class:`~ccf.agents.assembler.ContextAssemblerProtocol` gives for its own
    case: a deployment substitutes its own resolver by **conforming**, and the
    SDK's reference implementation carries no privileged status.
    :class:`GovernedResolver` is something a deployment instantiates and
    supplies — never something the SDK invokes on its own authority.

    ``@runtime_checkable`` so a delivery surface can assert conformance at the
    boundary it is handed one, rather than discovering a shape mismatch inside
    a call it has already accepted. The check is structural and covers the
    presence of ``__call__``, not its signature; the signature is mypy's job,
    and this module is inside ``[tool.mypy] files``.

    **Two refusals a resolver must call, and no door will call for it.** This
    obligation is inherited verbatim from the two ``runtime/`` seams, whose
    docstrings argue it at length, and it is restated rather than referenced
    because a resolver author reading *this* Protocol is the person it falls
    on:

    - A resolver that does not call
      :func:`~ccf.products.request.refuse_request` **serves against an
      unchecked request** — the question is answered without ever being
      compared to the surface its product class declared.
    - A resolver that does not call
      :func:`~ccf.products.bind.refuse_bound_payload` **serves an unvalidated
      payload against a schema its own class declared**, which from a
      consumer's seat is indistinguishable from there being no schema at all.

    **Why a delivery surface cannot make either call for the resolver.** Both
    comparisons take the :class:`~ccf.products.contract.RegisteredProductClass`
    as their second operand, and a surface holding a tenant, a class name, a
    version, a perspective and a request holds no such thing — the registered
    class is resolved *behind* this seam. The SDK cannot call a comparison
    whose second operand it does not have, and reaching for it at the surface
    would put an SDK-owned verdict on the serve path that ``D-IMPL-102`` limb 3
    declined. :class:`GovernedResolver` discharges the obligation; a deployment
    writing its own discharges it itself.
    """

    def __call__(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """Return the gate-admitted product at that address, or the refusal.

        Keyword-only, so a signature of same-typed strings cannot be called
        with the tenant and the class transposed.

        Args:
            tenant: The tenant the product is addressed under. Established by
                the calling surface, never claimed by the caller's body.
            product_class: The Context Product class being requested.
            version: The class's own semver lane (INV-CH7-49). Lanes are per
                class and are never compared across classes.
            perspective: The Π role-conditioning the surface resolved and the
                deployment's entitlement policy authorized. Required and
                non-nullable, and deliberately not defaulted: a resolver
                quietly constructing its own perspective is indistinguishable
                from one honouring the surface's, and a parameter defaulting to
                ``None`` would recreate exactly that ambiguity one layer down.
            request: The typed question the caller asked, or ``None`` when
                **the surface carries no way to ask**. Required with no
                default; ``None`` is a positive assertion rather than a missing
                value, and it is spelled that way because the ``ccf-product://``
                template has three segments and no query surface among them.
                A surface that does have one passes a request whenever a caller
                supplies one.

        Returns:
            A :class:`~ccf.replay.serve.ServedProduct` — the vessel paired with
            the reference of the replay record whose successful append
            authorized its delivery — or a
            :class:`~ccf.products.refusal.RefusalEnvelope` carrying the
            governed "no" with its kind intact.

        Raises:
            ProductNotResolvable: no product at that address.
        """
        ...
