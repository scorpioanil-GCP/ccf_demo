"""L6 — Context Products, the System of Delivery.

Whitepaper §6.3 (the Context Product Contract specification) and §7.6 (the
delivery layer and its three validation gates); DESIGN.md §2B.3.

A Context Product is a typed, governed, decision-ready unit of meaning shaped
jointly by Intent, Perspective, Time, and Policy (INV-CH6-02) — runtime
assembled, TTL-bound, policy-formative. It is not a data product with better
manners.

Four modules: :mod:`ccf.products.contract` declares the typed contract and the
product-class registration that MAX_TTL configuration hangs off,
:mod:`ccf.products.gates` holds the three-gate sequence, which is the *only*
construction path of anything servable, :mod:`ccf.products.entitlement`
declares the Control Plane artifact stating which product classes a principal
may be served and which roles it may assert — ``P`` applied at delivery, where
the operators apply it during assembly (CLAUDE.md §8.3;
``docs/CONTEXT_PRODUCT_REVISION.md`` §10) — and :mod:`ccf.products.payload`
holds the **declared payload schema** a product class registers and the one
pure comparison that decides whether a payload conforms to it (D-IMPL-97
ruling 1; D-IMPL-102, which put schema validity at registration and payload
conformity at bind and added **no** fourth gate; D-IMPL-103, which widened the
already-proven declaration machinery by one level of nesting rather than
inventing a second one).

The three validation gates remain three. Nothing in
:mod:`ccf.products.payload` is reachable from :func:`ccf.products.gates.run_gates`,
and :class:`~ccf.products.payload.PayloadSchemaViolation` deliberately does not
derive from :class:`~ccf.products.gates.GateRefusal`, so a payload verdict
cannot travel as a gate verdict even by accident.

The package re-exports nothing, deliberately: a second import path for the same
symbol is a second surface the drift manifest has to track.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
